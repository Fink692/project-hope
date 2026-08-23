import hashlib
import hmac
import logging
from datetime import timedelta
from smtplib import SMTPException
from urllib.parse import urlencode

from django.conf import settings
from django.contrib.auth.tokens import default_token_generator
from django.core.exceptions import ValidationError
from django.core.mail import send_mail
from django.db import IntegrityError, transaction
from django.db.models import F, Q
from django.utils import timezone
from django.utils.encoding import force_bytes, force_str
from django.utils.http import urlsafe_base64_decode, urlsafe_base64_encode

from .models import PasswordResetDelivery, User


logger = logging.getLogger(__name__)


def password_fingerprint(user):
    return hashlib.sha256(user.password.encode("utf-8")).hexdigest()


def queue_password_reset(user):
    """Queue delivery without storing a reset credential or waiting for SMTP."""

    with transaction.atomic():
        delivery = (
            PasswordResetDelivery.objects.select_for_update()
            .filter(user=user, status=PasswordResetDelivery.Status.PENDING)
            .first()
        )
        created = delivery is None
        expires_at = timezone.now() + timedelta(
            seconds=settings.PROJECT_HOPE_PASSWORD_RESET_QUEUE_MAX_AGE_SECONDS
        )
        fingerprint = password_fingerprint(user)
        if created:
            try:
                with transaction.atomic():
                    delivery = PasswordResetDelivery.objects.create(
                        user=user,
                        password_fingerprint=fingerprint,
                        expires_at=expires_at,
                    )
            except IntegrityError:
                delivery = PasswordResetDelivery.objects.select_for_update().get(
                    user=user,
                    status=PasswordResetDelivery.Status.PENDING,
                )
                created = False
        if not created:
            delivery.password_fingerprint = fingerprint
            delivery.expires_at = expires_at
            delivery.email_sent_at = None
            delivery.email_last_attempt_at = None
            delivery.email_attempts = 0
            delivery.save(
                update_fields=[
                    "password_fingerprint",
                    "expires_at",
                    "email_sent_at",
                    "email_last_attempt_at",
                    "email_attempts",
                    "updated_at",
                ]
            )
    return delivery, created


def password_reset_credentials(user):
    return {
        "uid": urlsafe_base64_encode(force_bytes(user.pk)),
        "token": default_token_generator.make_token(user),
    }


def password_reset_user(uid, token, *, for_update=False):
    try:
        user_id = force_str(urlsafe_base64_decode(uid))
    except (TypeError, ValueError, OverflowError, UnicodeDecodeError):
        return None
    users = User.objects
    if for_update:
        users = users.select_for_update()
    try:
        user = users.get(pk=user_id, is_active=True)
    except (User.DoesNotExist, ValueError, ValidationError):
        return None
    return user if default_token_generator.check_token(user, token) else None


def send_password_reset(user):
    credentials = password_reset_credentials(user)
    # Keep both credentials in the fragment to avoid common proxy, server, and
    # referrer logs. The web client exchanges them with the API using POST.
    reset_url = (
        f"{settings.PROJECT_HOPE_PUBLIC_URL}/#"
        f"{urlencode({'reset_uid': credentials['uid'], 'reset_token': credentials['token']})}"
    )
    timeout_minutes = max(1, settings.PASSWORD_RESET_TIMEOUT // 60)
    try:
        return (
            send_mail(
                "Reset your Project Hope password",
                (
                    f"Hello {user.display_name},\n\n"
                    "A password reset was requested for your Project Hope account.\n\n"
                    "Open this private link to choose a new password:\n"
                    f"{reset_url}\n\n"
                    f"The link expires in {timeout_minutes} minutes and stops working "
                    "after your password changes. If you did not request this, ignore "
                    "the message and your password will stay the same.\n\n"
                    "Project Hope"
                ),
                settings.DEFAULT_FROM_EMAIL,
                [user.email],
                fail_silently=False,
            )
            == 1
        )
    except (OSError, SMTPException):
        logger.exception(
            "Password reset email delivery failed",
            extra={"user_id": str(user.id)},
        )
        return False


def send_password_reset_delivery(delivery):
    now = timezone.now()
    cutoff = now - timedelta(
        seconds=settings.PROJECT_HOPE_PASSWORD_RESET_EMAIL_RETRY_SECONDS
    )
    claimed = (
        PasswordResetDelivery.objects.filter(
            id=delivery.id,
            status=PasswordResetDelivery.Status.PENDING,
            expires_at__gt=now,
        )
        .filter(
            Q(email_last_attempt_at__isnull=True) | Q(email_last_attempt_at__lte=cutoff)
        )
        .update(
            email_attempts=F("email_attempts") + 1,
            email_last_attempt_at=now,
            updated_at=now,
        )
    )
    if claimed != 1:
        return False

    delivery = PasswordResetDelivery.objects.select_related("user").get(id=delivery.id)
    password_unchanged = hmac.compare_digest(
        delivery.password_fingerprint,
        password_fingerprint(delivery.user),
    )
    if (
        delivery.status != PasswordResetDelivery.Status.PENDING
        or delivery.expires_at <= now
        or not delivery.user.is_active
        or not password_unchanged
    ):
        PasswordResetDelivery.objects.filter(id=delivery.id).update(
            status=PasswordResetDelivery.Status.CANCELLED,
            updated_at=now,
        )
        return False

    delivered = send_password_reset(delivery.user)
    if delivered:
        PasswordResetDelivery.objects.filter(
            id=delivery.id,
            status=PasswordResetDelivery.Status.PENDING,
            password_fingerprint=delivery.password_fingerprint,
        ).update(
            status=PasswordResetDelivery.Status.SENT,
            email_sent_at=now,
            updated_at=now,
        )
    return delivered
