import os

from django.core.management.base import BaseCommand
from django.db import transaction

from identity.models import Membership, Organization, User
from modules.models import AIModelRegistry, MetricDefinition, RetentionPolicy


class Command(BaseCommand):
    help = "Create or update the local Project Hope demo organization and owner."

    @transaction.atomic
    def handle(self, *args, **options):
        password = os.environ.get("DEMO_ADMIN_PASSWORD", "change-me-now")
        email = "demo@example.org"
        user, created = User.objects.get_or_create(
            email=email,
            defaults={
                "first_name": "Demo",
                "last_name": "Administrator",
                "is_active": True,
            },
        )
        if created or not user.check_password(password):
            user.set_password(password)
            user.is_active = True
            user.save(update_fields=["password", "is_active"])
        organization, _ = Organization.objects.get_or_create(
            slug="hope-demo",
            defaults={"name": "Project Hope Demo Charity"},
        )
        Membership.objects.update_or_create(
            organization=organization,
            user=user,
            defaults={"role": Membership.Role.OWNER, "active": True},
        )
        AIModelRegistry.objects.update_or_create(
            organization=organization,
            immutable_identifier="deterministic-local-adapter-v1",
            defaults={
                "name": "Deterministic local safety adapter",
                "checksum": "built-in",
                "license": "Project Hope source license",
                "intended_tasks": [
                    "classification",
                    "reviewable drafting",
                    "translation fallback",
                ],
                "prohibited_tasks": [
                    "side effects",
                    "eligibility decisions",
                    "crisis advice",
                ],
                "enabled": True,
            },
        )
        MetricDefinition.objects.get_or_create(
            organization=organization,
            key="volunteer_hours",
            defaults={
                "name": "Volunteer hours",
                "definition": "Approved attendance hours recorded for volunteer shifts.",
                "unit": "hours",
                "owner": user,
            },
        )
        RetentionPolicy.objects.get_or_create(
            organization=organization,
            record_type="workflows",
            defaults={"retention_days": 365, "legal_hold": False, "enabled": True},
        )
        self.stdout.write(
            self.style.SUCCESS(
                f"Demo data ready: {email} / configured DEMO_ADMIN_PASSWORD"
            )
        )
