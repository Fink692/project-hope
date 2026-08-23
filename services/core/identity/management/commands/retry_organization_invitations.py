import json
from datetime import timedelta

from django.conf import settings
from django.core.management.base import BaseCommand
from django.db.models import Q
from django.utils import timezone

from identity.invitations import send_team_invitation
from identity.models import OrganizationInvitation


class Command(BaseCommand):
    help = "Retry pending team invitations not accepted by the SMTP relay."

    def handle(self, *args, **options):
        now = timezone.now()
        cutoff = now - timedelta(
            seconds=settings.PROJECT_HOPE_INVITATION_EMAIL_RETRY_SECONDS
        )
        pending = (
            OrganizationInvitation.objects.filter(
                status=OrganizationInvitation.Status.PENDING,
                expires_at__gt=now,
                email_sent_at__isnull=True,
            )
            .filter(
                Q(email_last_attempt_at__isnull=True)
                | Q(email_last_attempt_at__lte=cutoff)
            )
            .select_related("organization", "invited_by")[
                : settings.PROJECT_HOPE_INVITATION_EMAIL_RETRY_BATCH_SIZE
            ]
        )
        attempted = 0
        delivered = 0
        for invitation in pending:
            attempted += 1
            if send_team_invitation(invitation):
                delivered += 1
        if options["verbosity"] > 0:
            self.stdout.write(
                json.dumps(
                    {"attempted": attempted, "delivered": delivered}, sort_keys=True
                )
            )
