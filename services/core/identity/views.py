from django.conf import settings
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.password_validation import validate_password
from django.core import signing
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import IntegrityError, transaction
from django.db.models import F
from django.http import Http404
from django.middleware.csrf import get_token
from django.utils import timezone
from django.utils.text import slugify
from django.views.decorators.csrf import ensure_csrf_cookie
from django.utils.decorators import method_decorator
from rest_framework import status
from rest_framework.authentication import BaseAuthentication, SessionAuthentication
from rest_framework.authtoken.models import Token
from rest_framework.permissions import AllowAny, IsAdminUser, IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView

from audit.models import AuditEvent

from .authentication import token_is_expired
from .invitations import (
    invitation_expiry,
    invitation_payload,
    prepare_team_invitation,
    send_team_invitation,
)
from .models import (
    Membership,
    Organization,
    OrganizationInvitation,
    PasswordResetDelivery,
    PilotApplication,
    User,
)
from .pilot import (
    PILOT_VERIFICATION_SALT,
    send_pilot_verification,
    verification_email_due,
)
from .passwords import password_reset_user, queue_password_reset
from .permissions import active_membership, require_admin, require_membership
from .serializers import (
    AcceptOrganizationInvitationSerializer,
    AddMembershipSerializer,
    CreateOrganizationInvitationSerializer,
    CreateOrganizationSerializer,
    InvitationTokenSerializer,
    LoginSerializer,
    MembershipSerializer,
    OrganizationInvitationSerializer,
    OrganizationSerializer,
    PasswordResetConfirmSerializer,
    PasswordResetRequestSerializer,
    PasswordResetTokenSerializer,
    PilotApplicationSerializer,
    PilotVerificationSerializer,
    UpdateMembershipSerializer,
    UserSummarySerializer,
)
from .throttles import LoginAccountRateThrottle


def scoped_organization(request, slug):
    organization = (
        Organization.objects.filter(
            slug=slug, memberships__user=request.user, memberships__active=True
        )
        .distinct()
        .first()
    )
    if organization is None:
        raise Http404
    return organization


def current_membership(request, organization):
    return active_membership(request.user, organization)


class InvalidInvitation(Exception):
    pass


def invitation_from_token(token, *, for_update=False):
    payload = invitation_payload(token)
    invitations = OrganizationInvitation.objects.select_related(
        "organization", "invited_by"
    )
    if for_update:
        # invited_by is nullable, so PostgreSQL rejects a broad FOR UPDATE across
        # the outer join. Lock only the invitation row that guards one-time use.
        invitations = invitations.select_for_update(of=("self",))
    try:
        invitation = invitations.get(id=payload["id"])
    except (OrganizationInvitation.DoesNotExist, DjangoValidationError) as exc:
        raise InvalidInvitation from exc
    if (
        invitation.status != OrganizationInvitation.Status.PENDING
        or invitation.email != payload["email"]
        or invitation.token_version != payload["version"]
        or invitation.expires_at <= timezone.now()
    ):
        raise InvalidInvitation
    return invitation


@method_decorator(ensure_csrf_cookie, name="dispatch")
class CsrfView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        return Response({"csrfTokenAvailable": bool(get_token(request))})


class PilotApplicationView(APIView):
    authentication_classes: list[type[BaseAuthentication]] = []
    permission_classes = [AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "pilot_application"

    def post(self, request):
        serializer = PilotApplicationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = dict(serializer.validated_data)

        # Real visitors never see or use this field. Treat a filled honeypot exactly
        # like a successful submission so bots cannot tune around it.
        if data.pop("company_website", ""):
            return Response(
                {
                    "detail": (
                        "Application received. Check your email to confirm your request."
                    )
                },
                status=status.HTTP_202_ACCEPTED,
            )

        email = data.pop("email")
        data["privacy_version"] = PilotApplication.PRIVACY_VERSION
        application, created = PilotApplication.objects.get_or_create(
            email=email,
            defaults=data,
        )
        if not created:
            PilotApplication.objects.filter(id=application.id).update(
                submission_count=F("submission_count") + 1,
                updated_at=timezone.now(),
            )
            application.refresh_from_db(fields=["submission_count", "updated_at"])

        if verification_email_due(application):
            send_pilot_verification(application)

        return Response(
            {
                "detail": (
                    "Application received. Check your email to confirm your request."
                )
            },
            status=status.HTTP_202_ACCEPTED,
        )


class PilotVerificationView(APIView):
    authentication_classes: list[type[BaseAuthentication]] = []
    permission_classes = [AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "pilot_verification"

    def post(self, request):
        serializer = PilotVerificationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            payload = signing.loads(
                serializer.validated_data["token"],
                salt=PILOT_VERIFICATION_SALT,
                max_age=settings.PROJECT_HOPE_PILOT_VERIFICATION_MAX_AGE_SECONDS,
            )
            application = PilotApplication.objects.get(
                id=payload["id"], email=payload["email"]
            )
        except (
            KeyError,
            PilotApplication.DoesNotExist,
            signing.BadSignature,
            signing.SignatureExpired,
            TypeError,
            ValueError,
        ):
            return Response(
                {"detail": "This confirmation link is invalid or has expired."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if application.verified_at is None:
            application.verified_at = timezone.now()
            application.save(update_fields=["verified_at", "updated_at"])

        return Response(
            {
                "detail": (
                    "Your email is confirmed. We will review your application and "
                    "contact you personally."
                ),
                "verified": True,
            }
        )


class PilotMetricsView(APIView):
    permission_classes = [IsAdminUser]

    def get(self, request):
        applications = PilotApplication.objects.all()
        verified = applications.filter(verified_at__isnull=False)
        status_counts = {
            choice: verified.filter(status=choice).count()
            for choice in PilotApplication.Status.values
        }
        verified_count = verified.count()
        return Response(
            {
                "target": 10,
                "applications": applications.count(),
                "verified": verified_count,
                "remaining": max(0, 10 - verified_count),
                "qualified": verified.filter(
                    status__in=[
                        PilotApplication.Status.QUALIFIED,
                        PilotApplication.Status.PILOT,
                        PilotApplication.Status.CONVERTED,
                    ]
                ).count(),
                "activePilots": status_counts[PilotApplication.Status.PILOT],
                "converted": status_counts[PilotApplication.Status.CONVERTED],
                "awaitingEmailDelivery": applications.filter(
                    verified_at__isnull=True, verification_email_sent_at__isnull=True
                ).count(),
                "byStatus": status_counts,
            }
        )


class InvitationInspectView(APIView):
    permission_classes = [AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "invitation_public"

    def post(self, request):
        serializer = InvitationTokenSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            invitation = invitation_from_token(serializer.validated_data["token"])
        except (InvalidInvitation, signing.BadSignature, TypeError, ValueError):
            return Response(
                {"detail": "This invitation is invalid, expired, or no longer active."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return Response(
            {
                "organization": {"name": invitation.organization.name},
                "email": invitation.email,
                "role": invitation.role,
                "roleLabel": invitation.get_role_display(),
                "expiresAt": invitation.expires_at,
                "existingAccount": User.objects.filter(
                    email__iexact=invitation.email, is_active=True
                ).exists(),
            }
        )


class InvitationAcceptView(APIView):
    permission_classes = [AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "invitation_public"

    def post(self, request):
        serializer = AcceptOrganizationInvitationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        token = serializer.validated_data["token"]

        try:
            with transaction.atomic():
                invitation = invitation_from_token(token, for_update=True)
                if (
                    request.user.is_authenticated
                    and request.user.email.lower() != invitation.email
                ):
                    return Response(
                        {
                            "detail": (
                                "Sign out before accepting an invitation for a "
                                "different email address."
                            )
                        },
                        status=status.HTTP_403_FORBIDDEN,
                    )

                user = User.objects.filter(email__iexact=invitation.email).first()
                created_account = user is None
                if user is not None and not user.is_active:
                    return Response(
                        {
                            "detail": (
                                "This account is inactive. Ask an administrator for help."
                            )
                        },
                        status=status.HTTP_400_BAD_REQUEST,
                    )

                if created_account:
                    password = serializer.validated_data.get("password", "")
                    if not password:
                        return Response(
                            {"password": ["Choose a password to create your account."]},
                            status=status.HTTP_400_BAD_REQUEST,
                        )
                    user = User(
                        email=invitation.email,
                        first_name=serializer.validated_data.get("first_name", ""),
                        last_name=serializer.validated_data.get("last_name", ""),
                    )
                    try:
                        validate_password(password, user=user)
                    except DjangoValidationError as exc:
                        return Response(
                            {"password": exc.messages},
                            status=status.HTTP_400_BAD_REQUEST,
                        )
                    user.set_password(password)
                    try:
                        with transaction.atomic():
                            user.save()
                    except IntegrityError:
                        user = User.objects.filter(
                            email__iexact=invitation.email
                        ).first()
                        if user is None:
                            raise
                        created_account = False
                        if not user.is_active:
                            return Response(
                                {
                                    "detail": (
                                        "This account is inactive. Ask an "
                                        "administrator for help."
                                    )
                                },
                                status=status.HTTP_400_BAD_REQUEST,
                            )

                membership, membership_created = Membership.objects.get_or_create(
                    organization=invitation.organization,
                    user=user,
                    defaults={"role": invitation.role, "active": True},
                )
                if not membership_created and (
                    membership.role != invitation.role or not membership.active
                ):
                    membership.role = invitation.role
                    membership.active = True
                    membership.save(update_fields=["role", "active", "updated_at"])

                invitation.status = OrganizationInvitation.Status.ACCEPTED
                invitation.accepted_at = timezone.now()
                invitation.save(update_fields=["status", "accepted_at", "updated_at"])
                AuditEvent.objects.record(
                    action="invitation.accepted",
                    actor=user,
                    organization=invitation.organization,
                    event_type="authorization",
                    resource_type="organization_invitation",
                    resource_id=invitation.id,
                    metadata={
                        "role": invitation.role,
                        "created_account": created_account,
                    },
                    request=request,
                )
        except (InvalidInvitation, signing.BadSignature, TypeError, ValueError):
            return Response(
                {"detail": "This invitation is invalid, expired, or no longer active."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        signed_in = request.user.is_authenticated
        if created_account:
            login(
                request,
                user,
                backend="django.contrib.auth.backends.ModelBackend",
            )
            signed_in = True
        return Response(
            {
                "detail": (
                    f"You have joined {invitation.organization.name}."
                    if signed_in
                    else (
                        f"Invitation accepted. Sign in as {invitation.email} to open "
                        f"{invitation.organization.name}."
                    )
                ),
                "signedIn": signed_in,
                "createdAccount": created_account,
                "organization": OrganizationSerializer(invitation.organization).data,
                "user": UserSummarySerializer(user).data,
            }
        )


class PasswordResetRequestView(APIView):
    authentication_classes: list[type[BaseAuthentication]] = []
    permission_classes = [AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "password_reset_request"

    def post(self, request):
        serializer = PasswordResetRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = User.objects.filter(
            email__iexact=serializer.validated_data["email"], is_active=True
        ).first()
        if user is not None and user.has_usable_password():
            delivery, _ = queue_password_reset(user)
            AuditEvent.objects.record(
                action="password.reset_queued",
                actor=user,
                event_type="authentication",
                resource_type="password_reset_delivery",
                resource_id=delivery.id,
                request=request,
            )
        return Response(
            {
                "detail": (
                    "If an active account matches that email, private reset "
                    "instructions will arrive shortly."
                )
            },
            status=status.HTTP_202_ACCEPTED,
        )


class PasswordResetInspectView(APIView):
    authentication_classes: list[type[BaseAuthentication]] = []
    permission_classes = [AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "password_reset_token"

    def post(self, request):
        serializer = PasswordResetTokenSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = password_reset_user(**serializer.validated_data)
        if user is None:
            return Response(
                {"detail": "This password reset link is invalid or has expired."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return Response({"email": user.email, "valid": True})


class PasswordResetConfirmView(APIView):
    permission_classes = [AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "password_reset_token"

    def post(self, request):
        serializer = PasswordResetConfirmSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        with transaction.atomic():
            user = password_reset_user(
                serializer.validated_data["uid"],
                serializer.validated_data["token"],
                for_update=True,
            )
            if user is None:
                return Response(
                    {"detail": "This password reset link is invalid or has expired."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            if request.user.is_authenticated and request.user.id != user.id:
                return Response(
                    {
                        "detail": (
                            "Sign out before resetting a different account's password."
                        )
                    },
                    status=status.HTTP_403_FORBIDDEN,
                )
            try:
                validate_password(serializer.validated_data["password"], user=user)
            except DjangoValidationError as exc:
                return Response(
                    {"password": exc.messages},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            user.set_password(serializer.validated_data["password"])
            user.save(update_fields=["password"])
            Token.objects.filter(user=user).delete()
            PasswordResetDelivery.objects.filter(
                user=user, status=PasswordResetDelivery.Status.PENDING
            ).update(
                status=PasswordResetDelivery.Status.CANCELLED,
                updated_at=timezone.now(),
            )
            AuditEvent.objects.record(
                action="password.reset_completed",
                actor=user,
                event_type="authentication",
                resource_type="user",
                resource_id=user.id,
                request=request,
            )
        if request.user.is_authenticated:
            logout(request)
        return Response(
            {
                "detail": (
                    "Your password has been changed. Sign in with the new password."
                ),
                "email": user.email,
            }
        )


class LoginView(APIView):
    permission_classes = [AllowAny]
    throttle_classes = [LoginAccountRateThrottle, ScopedRateThrottle]
    throttle_scope = "auth_login_ip"

    def post(self, request):
        SessionAuthentication().enforce_csrf(request)
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = authenticate(
            request,
            username=serializer.validated_data["email"],
            password=serializer.validated_data["password"],
        )
        if user is None or not user.is_active:
            return Response(
                {"detail": "Invalid credentials."}, status=status.HTTP_400_BAD_REQUEST
            )

        login(request, user)
        AuditEvent.objects.record(
            action="auth.login",
            actor=user,
            event_type="authentication",
            request=request,
        )
        return Response({"user": UserSummarySerializer(user).data})


class TokenLoginView(APIView):
    authentication_classes: list[type[BaseAuthentication]] = []
    permission_classes = [AllowAny]
    throttle_classes = [LoginAccountRateThrottle, ScopedRateThrottle]
    throttle_scope = "auth_login_ip"

    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = authenticate(
            request,
            username=serializer.validated_data["email"],
            password=serializer.validated_data["password"],
        )
        if user is None or not user.is_active:
            return Response(
                {"detail": "Invalid credentials."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        token, _ = Token.objects.get_or_create(user=user)
        if token_is_expired(token):
            token.delete()
            token = Token.objects.create(user=user)
        AuditEvent.objects.record(
            action="auth.token_issued",
            actor=user,
            event_type="authentication",
            resource_type="user",
            resource_id=user.id,
            request=request,
        )
        return Response({"user": UserSummarySerializer(user).data, "token": token.key})


class LogoutView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        user = request.user
        AuditEvent.objects.record(
            action="auth.logout",
            actor=user,
            event_type="authentication",
            request=request,
        )
        Token.objects.filter(user=user).delete()
        logout(request)
        return Response({"detail": "Logged out."})


class MeView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        memberships = (
            Membership.objects.select_related("organization")
            .filter(user=request.user, active=True)
            .order_by("organization__name")
        )
        return Response(
            {
                "user": UserSummarySerializer(request.user).data,
                "organizations": [
                    {
                        "organization": OrganizationSerializer(
                            membership.organization
                        ).data,
                        "role": membership.role,
                        "membershipId": str(membership.id),
                    }
                    for membership in memberships
                ],
            }
        )


class OrganizationListCreateView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        organizations = (
            Organization.objects.filter(
                memberships__user=request.user, memberships__active=True
            )
            .distinct()
            .order_by("name")
        )
        return Response(OrganizationSerializer(organizations, many=True).data)

    @transaction.atomic
    def post(self, request):
        serializer = CreateOrganizationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        name = serializer.validated_data["name"].strip()
        slug = serializer.validated_data.get("slug", "").strip() or slugify(name)
        if not name or not slug:
            return Response(
                {"detail": "A non-empty organization name is required."}, status=400
            )
        if Organization.objects.filter(slug=slug).exists():
            return Response(
                {"detail": "That organization slug is already in use."}, status=400
            )

        organization = Organization.objects.create(name=name, slug=slug)
        membership = Membership.objects.create(
            organization=organization,
            user=request.user,
            role=Membership.Role.OWNER,
        )
        AuditEvent.objects.record(
            action="organization.created",
            actor=request.user,
            organization=organization,
            event_type="organization",
            resource_type="organization",
            resource_id=organization.id,
            metadata={"slug": organization.slug},
            request=request,
        )
        AuditEvent.objects.record(
            action="membership.created",
            actor=request.user,
            organization=organization,
            event_type="authorization",
            resource_type="membership",
            resource_id=membership.id,
            metadata={"role": membership.role, "user_id": str(request.user.id)},
            request=request,
        )
        return Response(
            OrganizationSerializer(organization).data, status=status.HTTP_201_CREATED
        )


class OrganizationDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, slug):
        organization = scoped_organization(request, slug)
        membership = current_membership(request, organization)
        return Response(
            {
                "organization": OrganizationSerializer(organization).data,
                "role": membership.role,
            }
        )

    def patch(self, request, slug):
        organization = scoped_organization(request, slug)
        require_admin(require_membership(request.user, organization))
        allowed = {"name", "status"}
        unknown = set(request.data) - allowed
        if unknown:
            return Response(
                {"detail": "Unknown organization fields.", "fields": sorted(unknown)},
                status=400,
            )
        if "name" in request.data:
            name = str(request.data["name"]).strip()
            if not name:
                return Response({"detail": "Name cannot be empty."}, status=400)
            organization.name = name
        if "status" in request.data:
            if request.data["status"] not in Organization.Status.values:
                return Response({"detail": "Invalid organization status."}, status=400)
            organization.status = request.data["status"]
        organization.save(update_fields=["name", "status", "updated_at"])
        AuditEvent.objects.record(
            action="organization.updated",
            actor=request.user,
            organization=organization,
            event_type="organization",
            resource_type="organization",
            resource_id=organization.id,
            metadata={"fields": sorted(set(request.data) & allowed)},
            request=request,
        )
        return Response(OrganizationSerializer(organization).data)


class OrganizationInvitationListCreateView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, slug):
        organization = scoped_organization(request, slug)
        require_admin(require_membership(request.user, organization))
        invitations = OrganizationInvitation.objects.filter(
            organization=organization
        ).select_related("invited_by")[:100]
        return Response(OrganizationInvitationSerializer(invitations, many=True).data)

    def post(self, request, slug):
        organization = scoped_organization(request, slug)
        actor_membership = require_admin(require_membership(request.user, organization))
        serializer = CreateOrganizationInvitationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        email = serializer.validated_data["email"]
        role = serializer.validated_data["role"]
        if (
            role == Membership.Role.OWNER
            and actor_membership.role != Membership.Role.OWNER
        ):
            return Response(
                {"detail": "Only an owner may invite another owner."},
                status=status.HTTP_403_FORBIDDEN,
            )
        if Membership.objects.filter(
            organization=organization,
            user__email__iexact=email,
            active=True,
        ).exists():
            return Response(
                {"detail": "That person is already an active team member."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        invitation, created = prepare_team_invitation(
            organization=organization,
            email=email,
            role=role,
            invited_by=request.user,
        )

        delivered = send_team_invitation(invitation)
        invitation.refresh_from_db()
        AuditEvent.objects.record(
            action="invitation.created" if created else "invitation.refreshed",
            actor=request.user,
            organization=organization,
            event_type="authorization",
            resource_type="organization_invitation",
            resource_id=invitation.id,
            metadata={"role": role, "email_delivered": delivered},
            request=request,
        )
        return Response(
            OrganizationInvitationSerializer(invitation).data,
            status=(status.HTTP_201_CREATED if created else status.HTTP_200_OK),
        )


class OrganizationInvitationDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def delete(self, request, slug, invitation_id):
        organization = scoped_organization(request, slug)
        actor_membership = require_admin(require_membership(request.user, organization))
        with transaction.atomic():
            try:
                invitation = OrganizationInvitation.objects.select_for_update().get(
                    organization=organization, id=invitation_id
                )
            except OrganizationInvitation.DoesNotExist as exc:
                raise Http404 from exc
            if (
                invitation.role == Membership.Role.OWNER
                and actor_membership.role != Membership.Role.OWNER
            ):
                return Response(
                    {"detail": "Only an owner may revoke an owner invitation."},
                    status=status.HTTP_403_FORBIDDEN,
                )
            if invitation.status != OrganizationInvitation.Status.PENDING:
                return Response(
                    {"detail": "Only a pending invitation can be revoked."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            invitation.status = OrganizationInvitation.Status.REVOKED
            invitation.revoked_at = timezone.now()
            invitation.token_version += 1
            invitation.save(
                update_fields=[
                    "status",
                    "revoked_at",
                    "token_version",
                    "updated_at",
                ]
            )
            AuditEvent.objects.record(
                action="invitation.revoked",
                actor=request.user,
                organization=organization,
                event_type="authorization",
                resource_type="organization_invitation",
                resource_id=invitation.id,
                metadata={"role": invitation.role},
                request=request,
            )
        return Response(status=status.HTTP_204_NO_CONTENT)


class OrganizationInvitationResendView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, slug, invitation_id):
        organization = scoped_organization(request, slug)
        actor_membership = require_admin(require_membership(request.user, organization))
        with transaction.atomic():
            try:
                invitation = (
                    OrganizationInvitation.objects.select_for_update(of=("self",))
                    .select_related("invited_by", "organization")
                    .get(organization=organization, id=invitation_id)
                )
            except OrganizationInvitation.DoesNotExist as exc:
                raise Http404 from exc
            if (
                invitation.role == Membership.Role.OWNER
                and actor_membership.role != Membership.Role.OWNER
            ):
                return Response(
                    {"detail": "Only an owner may resend an owner invitation."},
                    status=status.HTTP_403_FORBIDDEN,
                )
            if invitation.status != OrganizationInvitation.Status.PENDING:
                return Response(
                    {"detail": "Only a pending invitation can be resent."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            invitation.token_version += 1
            invitation.expires_at = invitation_expiry()
            invitation.email_sent_at = None
            invitation.email_last_attempt_at = None
            invitation.email_attempts = 0
            invitation.invited_by = request.user
            invitation.save(
                update_fields=[
                    "token_version",
                    "expires_at",
                    "email_sent_at",
                    "email_last_attempt_at",
                    "email_attempts",
                    "invited_by",
                    "updated_at",
                ]
            )

        delivered = send_team_invitation(invitation)
        invitation.refresh_from_db()
        AuditEvent.objects.record(
            action="invitation.resent",
            actor=request.user,
            organization=organization,
            event_type="authorization",
            resource_type="organization_invitation",
            resource_id=invitation.id,
            metadata={"role": invitation.role, "email_delivered": delivered},
            request=request,
        )
        return Response(OrganizationInvitationSerializer(invitation).data)


class MembershipListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, slug):
        organization = scoped_organization(request, slug)
        require_membership(request.user, organization)
        memberships = Membership.objects.filter(
            organization=organization
        ).select_related("user")
        return Response(MembershipSerializer(memberships, many=True).data)

    @transaction.atomic
    def post(self, request, slug):
        organization = scoped_organization(request, slug)
        actor_membership = require_admin(require_membership(request.user, organization))
        serializer = AddMembershipSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        role = serializer.validated_data["role"]
        if (
            role == Membership.Role.OWNER
            and actor_membership.role != Membership.Role.OWNER
        ):
            return Response(
                {"detail": "Only an owner may assign the owner role."}, status=403
            )
        try:
            target = User.objects.get(email__iexact=serializer.validated_data["email"])
        except User.DoesNotExist:
            return Response({"detail": "User does not exist."}, status=404)
        if Membership.objects.filter(organization=organization, user=target).exists():
            return Response({"detail": "User is already a member."}, status=400)
        membership = Membership.objects.create(
            organization=organization, user=target, role=role
        )
        AuditEvent.objects.record(
            action="membership.created",
            actor=request.user,
            organization=organization,
            event_type="authorization",
            resource_type="membership",
            resource_id=membership.id,
            metadata={"role": role, "user_id": str(target.id)},
            request=request,
        )
        return Response(MembershipSerializer(membership).data, status=201)


class MembershipDetailView(APIView):
    permission_classes = [IsAuthenticated]

    @transaction.atomic
    def patch(self, request, slug, membership_id):
        organization = scoped_organization(request, slug)
        actor_membership = require_admin(require_membership(request.user, organization))
        # Serialize role changes for one organization so concurrent owner updates
        # cannot both pass the "last active owner" check.
        list(
            Membership.objects.select_for_update()
            .filter(organization=organization)
            .order_by("id")
            .values_list("id", flat=True)
        )
        try:
            membership = (
                Membership.objects.select_for_update()
                .select_related("user")
                .get(
                    organization=organization,
                    id=membership_id,
                )
            )
        except Membership.DoesNotExist as exc:
            raise Http404 from exc

        serializer = UpdateMembershipSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        changes = serializer.validated_data
        new_role = changes.get("role", membership.role)
        if (
            membership.role == Membership.Role.OWNER
            and actor_membership.role != Membership.Role.OWNER
        ):
            return Response(
                {"detail": "Only an owner may change an owner membership."}, status=403
            )
        if (
            new_role == Membership.Role.OWNER
            and actor_membership.role != Membership.Role.OWNER
        ):
            return Response(
                {"detail": "Only an owner may assign the owner role."}, status=403
            )
        if membership.role == Membership.Role.OWNER and (
            new_role != Membership.Role.OWNER or changes.get("active") is False
        ):
            remaining_owners = (
                Membership.objects.filter(
                    organization=organization,
                    role=Membership.Role.OWNER,
                    active=True,
                )
                .exclude(id=membership.id)
                .exists()
            )
            if not remaining_owners:
                return Response(
                    {"detail": "An organization must retain an active owner."},
                    status=400,
                )
        membership.role = new_role
        if "active" in changes:
            membership.active = changes["active"]
        membership.save(update_fields=["role", "active", "updated_at"])
        AuditEvent.objects.record(
            action="membership.updated",
            actor=request.user,
            organization=organization,
            event_type="authorization",
            resource_type="membership",
            resource_id=membership.id,
            metadata={
                "role": membership.role,
                "active": membership.active,
                "user_id": str(membership.user_id),
            },
            request=request,
        )
        return Response(MembershipSerializer(membership).data)


class AuditEventListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, slug):
        organization = scoped_organization(request, slug)
        require_admin(require_membership(request.user, organization))
        events = AuditEvent.objects.filter(organization=organization).select_related(
            "actor"
        )[:100]
        AuditEvent.objects.record(
            action="audit.read",
            actor=request.user,
            organization=organization,
            event_type="audit",
            resource_type="audit_event",
            metadata={"limit": 100},
            request=request,
        )
        return Response(
            [
                {
                    "id": str(event.id),
                    "eventType": event.event_type,
                    "action": event.action,
                    "resourceType": event.resource_type,
                    "resourceId": event.resource_id,
                    "actor": event.actor.email if event.actor else None,
                    "metadata": event.metadata,
                    "createdAt": event.created_at,
                }
                for event in events
            ]
        )
