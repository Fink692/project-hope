from django.conf import settings
from django.contrib.auth import authenticate, login, logout
from django.core import signing
from django.db import transaction
from django.db.models import F
from django.http import Http404
from django.middleware.csrf import get_token
from django.utils import timezone
from django.utils.text import slugify
from django.views.decorators.csrf import ensure_csrf_cookie
from django.utils.decorators import method_decorator
from rest_framework import status
from rest_framework.authentication import BaseAuthentication
from rest_framework.authtoken.models import Token
from rest_framework.permissions import AllowAny, IsAdminUser, IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView

from audit.models import AuditEvent

from .models import Membership, Organization, PilotApplication, User
from .pilot import (
    PILOT_VERIFICATION_SALT,
    send_pilot_verification,
    verification_email_due,
)
from .permissions import active_membership, require_admin, require_membership
from .serializers import (
    AddMembershipSerializer,
    CreateOrganizationSerializer,
    LoginSerializer,
    MembershipSerializer,
    OrganizationSerializer,
    PilotApplicationSerializer,
    PilotVerificationSerializer,
    UpdateMembershipSerializer,
    UserSummarySerializer,
)


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


class LoginView(APIView):
    permission_classes = [AllowAny]

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
                {"detail": "Invalid credentials."}, status=status.HTTP_400_BAD_REQUEST
            )

        login(request, user)
        token, _ = Token.objects.get_or_create(user=user)
        AuditEvent.objects.record(
            action="auth.login",
            actor=user,
            event_type="authentication",
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
        try:
            membership = Membership.objects.select_related("user").get(
                organization=organization,
                id=membership_id,
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
