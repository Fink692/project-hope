import logging
from datetime import timedelta
from smtplib import SMTPException
from urllib.parse import urlencode

from django.conf import settings
from django.core import signing
from django.core.mail import send_mail
from django.db.models import F
from django.utils import timezone

from .models import PilotApplication


logger = logging.getLogger(__name__)
PILOT_VERIFICATION_SALT = "project-hope.pilot-application"


def verification_email_due(application):
    if application.verified_at is not None:
        return False
    if application.verification_email_last_attempt_at is None:
        return True
    cutoff = timezone.now() - timedelta(
        seconds=settings.PROJECT_HOPE_PILOT_EMAIL_RETRY_SECONDS
    )
    return application.verification_email_last_attempt_at <= cutoff


def send_pilot_verification(application):
    token = signing.dumps(
        {"id": str(application.id), "email": application.email},
        salt=PILOT_VERIFICATION_SALT,
    )
    # Keep the signed token in the URL fragment. Browsers do not send fragments
    # to the web server or include them in HTTP referrers, which keeps the token
    # out of ordinary proxy and access logs.
    verification_url = (
        f"{settings.PROJECT_HOPE_PUBLIC_URL}/#{urlencode({'pilot_token': token})}"
    )
    max_age_days = max(
        1,
        (settings.PROJECT_HOPE_PILOT_VERIFICATION_MAX_AGE_SECONDS + 86399) // 86400,
    )
    attempted_at = timezone.now()
    delivered = False
    try:
        delivered = (
            send_mail(
                "Confirm your Project Hope Founding 10 application",
                (
                    f"Hello {application.contact_name},\n\n"
                    "Thank you for applying to the Project Hope Founding 10 "
                    f"programme for {application.organization_name}.\n\n"
                    "Confirm your email by opening this private link:\n"
                    f"{verification_url}\n\n"
                    f"The link expires in {max_age_days} days. After confirmation, "
                    "the Project Hope team can contact you about fit, scope, and "
                    "pricing. No payment has been taken. If you did not make this "
                    "request, ignore this message.\n\n"
                    "Project Hope"
                ),
                settings.DEFAULT_FROM_EMAIL,
                [application.email],
                fail_silently=False,
            )
            == 1
        )
    except (OSError, SMTPException):
        logger.exception(
            "Pilot verification email delivery failed",
            extra={"application_id": str(application.id)},
        )

    updates = {
        "verification_email_attempts": F("verification_email_attempts") + 1,
        "verification_email_last_attempt_at": attempted_at,
        "updated_at": attempted_at,
    }
    if delivered:
        updates["verification_email_sent_at"] = attempted_at
    PilotApplication.objects.filter(id=application.id).update(**updates)
    return delivered
