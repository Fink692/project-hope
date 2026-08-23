import json

from django.core.management.base import BaseCommand

from identity.models import PilotApplication


class Command(BaseCommand):
    help = "Print privacy-safe Founding 10 acquisition metrics as JSON."

    def handle(self, *args, **options):
        applications = PilotApplication.objects.all()
        verified = applications.filter(verified_at__isnull=False)
        verified_count = verified.count()
        metrics = {
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
            "active_pilots": verified.filter(
                status=PilotApplication.Status.PILOT
            ).count(),
            "converted": verified.filter(
                status=PilotApplication.Status.CONVERTED
            ).count(),
            "awaiting_email_delivery": applications.filter(
                verified_at__isnull=True,
                verification_email_sent_at__isnull=True,
            ).count(),
        }
        self.stdout.write(json.dumps(metrics, sort_keys=True))
