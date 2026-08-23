import logging
from datetime import timedelta
from smtplib import SMTPException
from urllib.parse import urlencode

from django.conf import settings
from django.core import signing
from django.core.mail import send_mail
from django.db import IntegrityError, transaction
from django.db.models import F, Q
from django.utils import timezone

from .models import OrganizationInvitation


logger = logging.getLogger(__name__)
TEAM_INVITATION_SALT = "project-hope.organization-invitation"


def invitation_expiry():
    return timezone.now() + timedelta(
        seconds=settings.PROJECT_HOPE_INVITATION_MAX_AGE_SECONDS
    )


def invitation_token(invitation):
    return signing.dumps(
        {
            "id": str(invitation.id),
            "email": invitation.email,
            "version": invitation.token_version,
        },
        salt=TEAM_INVITATION_SALT,
    )


def prepare_team_invitation(*, organization, email, role, invited_by=None):
    """Create or rotate a pending invitation without sending it."""

    normalized_email = email.strip().lower()
    with transaction.atomic():
        invitation = (
            OrganizationInvitation.objects.select_for_update()
            .filter(
                organization=organization,
                email=normalized_email,
                status=OrganizationInvitation.Status.PENDING,
            )
            .first()
        )
        created = invitation is None
        if created:
            try:
                with transaction.atomic():
                    invitation = OrganizationInvitation.objects.create(
                        organization=organization,
                        email=normalized_email,
                        role=role,
                        invited_by=invited_by,
                        expires_at=invitation_expiry(),
                    )
            except IntegrityError:
                invitation = OrganizationInvitation.objects.select_for_update().get(
                    organization=organization,
                    email=normalized_email,
                    status=OrganizationInvitation.Status.PENDING,
                )
                created = False
        if not created:
            invitation.role = role
            invitation.invited_by = invited_by
            invitation.token_version += 1
            invitation.expires_at = invitation_expiry()
            invitation.email_sent_at = None
            invitation.email_last_attempt_at = None
            invitation.email_attempts = 0
            invitation.save(
                update_fields=[
                    "role",
                    "invited_by",
                    "token_version",
                    "expires_at",
                    "email_sent_at",
                    "email_last_attempt_at",
                    "email_attempts",
                    "updated_at",
                ]
            )
    return invitation, created


def invitation_payload(token):
    payload = signing.loads(
        token,
        salt=TEAM_INVITATION_SALT,
        max_age=settings.PROJECT_HOPE_INVITATION_MAX_AGE_SECONDS,
    )
    if not isinstance(payload, dict):
        raise signing.BadSignature("Invitation payload is not an object.")
    invitation_id = payload.get("id")
    email = payload.get("email")
    version = payload.get("version")
    if not invitation_id or not isinstance(email, str) or not isinstance(version, int):
        raise signing.BadSignature("Invitation payload is incomplete.")
    return {
        "id": invitation_id,
        "email": email.strip().lower(),
        "version": version,
    }


def send_team_invitation(invitation):
    attempted_at = timezone.now()
    cutoff = attempted_at - timedelta(
        seconds=settings.PROJECT_HOPE_INVITATION_EMAIL_RETRY_SECONDS
    )
    claimed = (
        OrganizationInvitation.objects.filter(
            id=invitation.id,
            status=OrganizationInvitation.Status.PENDING,
            expires_at__gt=attempted_at,
            email_sent_at__isnull=True,
        )
        .filter(
            Q(email_last_attempt_at__isnull=True) | Q(email_last_attempt_at__lte=cutoff)
        )
        .update(
            email_attempts=F("email_attempts") + 1,
            email_last_attempt_at=attempted_at,
            updated_at=attempted_at,
        )
    )
    if claimed != 1:
        return False

    invitation = OrganizationInvitation.objects.select_related(
        "organization", "invited_by"
    ).get(id=invitation.id)
    if (
        invitation.status != OrganizationInvitation.Status.PENDING
        or invitation.expires_at <= attempted_at
        or invitation.email_sent_at is not None
    ):
        return False
    token_version = invitation.token_version

    token = invitation_token(invitation)
    # Fragments are not sent to the web server or ordinary HTTP referrers, which
    # keeps the one-time credential out of common proxy and access logs.
    accept_url = (
        f"{settings.PROJECT_HOPE_PUBLIC_URL}/#{urlencode({'invite_token': token})}"
    )
    inviter_name = (
        invitation.invited_by.display_name
        if invitation.invited_by is not None
        else "A Project Hope administrator"
    )
    max_age_days = max(
        1,
        (settings.PROJECT_HOPE_INVITATION_MAX_AGE_SECONDS + 86399) // 86400,
    )
    delivered = False
    try:
        delivered = (
            send_mail(
                f"Join {invitation.organization.name} in Project Hope",
                (
                    f"Hello,\n\n"
                    f"{inviter_name} invited you to join {invitation.organization.name} "
                    f"in Project Hope as {invitation.get_role_display().lower()}.\n\n"
                    "Open this private link to review and accept the invitation:\n"
                    f"{accept_url}\n\n"
                    f"The link expires in {max_age_days} days and can be used once. "
                    "If you were not expecting this invitation, ignore this message "
                    "or contact the organization directly.\n\n"
                    "Project Hope"
                ),
                settings.DEFAULT_FROM_EMAIL,
                [invitation.email],
                fail_silently=False,
            )
            == 1
        )
    except (OSError, SMTPException):
        logger.exception(
            "Organization invitation email delivery failed",
            extra={"invitation_id": str(invitation.id)},
        )

    if delivered:
        OrganizationInvitation.objects.filter(
            id=invitation.id,
            status=OrganizationInvitation.Status.PENDING,
            token_version=token_version,
        ).update(email_sent_at=attempted_at, updated_at=attempted_at)
    return delivered
