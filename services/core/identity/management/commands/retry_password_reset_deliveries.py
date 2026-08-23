import json
from datetime import timedelta

from django.conf import settings
from django.core.management.base import BaseCommand
from django.db.models import Q
from django.utils import timezone

from identity.models import PasswordResetDelivery
from identity.passwords import send_password_reset_delivery


class Command(BaseCommand):
    help = "Deliver queued password-reset email without exposing account existence."

    def handle(self, *args, **options):
        now = timezone.now()
        cutoff = now - timedelta(
            seconds=settings.PROJECT_HOPE_PASSWORD_RESET_EMAIL_RETRY_SECONDS
        )
        pending = (
            PasswordResetDelivery.objects.filter(
                status=PasswordResetDelivery.Status.PENDING,
                expires_at__gt=now,
            )
            .filter(
                Q(email_last_attempt_at__isnull=True)
                | Q(email_last_attempt_at__lte=cutoff)
            )
            .select_related("user")[
                : settings.PROJECT_HOPE_PASSWORD_RESET_EMAIL_RETRY_BATCH_SIZE
            ]
        )
        attempted = 0
        delivered = 0
        for delivery in pending:
            attempted += 1
            if send_password_reset_delivery(delivery):
                delivered += 1

        cancelled = PasswordResetDelivery.objects.filter(
            status=PasswordResetDelivery.Status.PENDING,
            expires_at__lte=now,
        ).update(status=PasswordResetDelivery.Status.CANCELLED, updated_at=now)
        retention_cutoff = now - timedelta(
            days=settings.PROJECT_HOPE_PASSWORD_RESET_DELIVERY_RETENTION_DAYS
        )
        purged, _ = PasswordResetDelivery.objects.filter(
            status__in=[
                PasswordResetDelivery.Status.SENT,
                PasswordResetDelivery.Status.CANCELLED,
            ],
            updated_at__lt=retention_cutoff,
        ).delete()
        if options["verbosity"] > 0:
            self.stdout.write(
                json.dumps(
                    {
                        "attempted": attempted,
                        "cancelled": cancelled,
                        "delivered": delivered,
                        "purged": purged,
                    },
                    sort_keys=True,
                )
            )
