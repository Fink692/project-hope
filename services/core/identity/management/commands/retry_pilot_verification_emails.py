import json
from datetime import timedelta

from django.conf import settings
from django.core.management.base import BaseCommand
from django.db.models import Q
from django.utils import timezone

from identity.models import PilotApplication
from identity.pilot import send_pilot_verification


class Command(BaseCommand):
    help = "Retry confirmation mail that was not accepted by the SMTP relay."

    def handle(self, *args, **options):
        cutoff = timezone.now() - timedelta(
            seconds=settings.PROJECT_HOPE_PILOT_EMAIL_RETRY_SECONDS
        )
        pending = PilotApplication.objects.filter(
            verified_at__isnull=True,
            verification_email_sent_at__isnull=True,
        ).filter(
            Q(verification_email_last_attempt_at__isnull=True)
            | Q(verification_email_last_attempt_at__lte=cutoff)
        )[: settings.PROJECT_HOPE_PILOT_EMAIL_RETRY_BATCH_SIZE]
        attempted = 0
        delivered = 0
        for application in pending:
            attempted += 1
            if send_pilot_verification(application):
                delivered += 1
        if options["verbosity"] > 0:
            self.stdout.write(
                json.dumps(
                    {"attempted": attempted, "delivered": delivered}, sort_keys=True
                )
            )
