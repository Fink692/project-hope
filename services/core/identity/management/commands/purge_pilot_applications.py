import json
from datetime import timedelta

from django.conf import settings
from django.core.management.base import BaseCommand
from django.db.models import Q
from django.utils import timezone

from identity.models import PilotApplication


class Command(BaseCommand):
    help = "Preview or execute the documented Founding 10 application retention rules."

    def add_arguments(self, parser):
        parser.add_argument(
            "--execute",
            action="store_true",
            help="Delete matching applications. Without this flag, only preview counts.",
        )

    def handle(self, *args, **options):
        now = timezone.now()
        unverified_cutoff = now - timedelta(
            days=settings.PROJECT_HOPE_PILOT_UNVERIFIED_RETENTION_DAYS
        )
        declined_cutoff = now - timedelta(
            days=settings.PROJECT_HOPE_PILOT_DECLINED_RETENTION_DAYS
        )
        inactive_cutoff = now - timedelta(
            days=settings.PROJECT_HOPE_PILOT_INACTIVE_RETENTION_DAYS
        )
        inactive_statuses = [
            PilotApplication.Status.NEW,
            PilotApplication.Status.CONTACTED,
            PilotApplication.Status.QUALIFIED,
        ]
        targets = PilotApplication.objects.filter(
            Q(verified_at__isnull=True, created_at__lt=unverified_cutoff)
            | Q(status=PilotApplication.Status.DECLINED, updated_at__lt=declined_cutoff)
            | Q(
                verified_at__isnull=False,
                status__in=inactive_statuses,
                updated_at__lt=inactive_cutoff,
            )
        )
        metrics = {
            "mode": "execute" if options["execute"] else "preview",
            "matched": targets.count(),
            "unverified_retention_days": (
                settings.PROJECT_HOPE_PILOT_UNVERIFIED_RETENTION_DAYS
            ),
            "declined_retention_days": (
                settings.PROJECT_HOPE_PILOT_DECLINED_RETENTION_DAYS
            ),
            "inactive_retention_days": (
                settings.PROJECT_HOPE_PILOT_INACTIVE_RETENTION_DAYS
            ),
        }
        if options["execute"]:
            deleted, _ = targets.delete()
            metrics["deleted"] = deleted
        if options["verbosity"] > 0:
            self.stdout.write(json.dumps(metrics, sort_keys=True))
