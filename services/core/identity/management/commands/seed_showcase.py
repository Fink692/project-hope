"""Synthetic records for the isolated desktop sample, never real applicants."""

from datetime import timedelta

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from identity.models import Membership, Organization, User
from modules.models import (
    CommunityResource,
    Contact,
    GrantWorkspace,
    Interaction,
    MetricDefinition,
    Program,
    ScheduleEvent,
    VolunteerApplication,
)


class Command(BaseCommand):
    help = "Seed a synthetic, local-only desktop showcase once."

    @transaction.atomic
    def handle(self, *args, **options):
        if settings.SETTINGS_MODULE != "project.desktop_settings":
            raise CommandError("Showcase data requires the isolated desktop settings.")
        organization, created = Organization.objects.get_or_create(
            slug="hope-showcase", defaults={"name": "Hope Community · sample workspace"}
        )
        if not created:
            return
        user = User.objects.create(
            email="showcase@example.org",
            first_name="Jamie",
            last_name="Morgan",
            is_active=True,
        )
        user.set_unusable_password()
        user.save(update_fields=["password"])
        Membership.objects.create(
            organization=organization,
            user=user,
            role=Membership.Role.OWNER,
            active=True,
        )
        now = timezone.now().replace(hour=10, minute=0, second=0, microsecond=0)
        people = [
            ("Alex", "Rivera", "volunteer", "Food pantry and community events"),
            ("Sam", "Chen", "volunteer", "Weekend reception and translation"),
            ("Jordan", "Patel", "donor", "Requested a copy of the community report"),
            ("Taylor", "Brooks", "person", "Community garden programme contact"),
            ("Casey", "Williams", "volunteer", "Available for the Saturday pantry"),
            ("Morgan", "Lee", "donor", "Prefers email updates; fictional sample"),
        ]
        for index, (first, last, kind, note) in enumerate(people):
            contact = Contact.objects.create(
                organization=organization,
                first_name=first,
                last_name=last,
                contact_type=kind,
                email=f"{first.lower()}.{last.lower()}@example.org",
                external_ref=f"SAMPLE-{index + 1:03d}",
                consent_status="granted",
                notes=f"Synthetic demonstration record. {note}.",
            )
            Interaction.objects.create(
                organization=organization,
                contact=contact,
                subject="Sample welcome conversation",
                body="Fictional conversation for exploring the contact timeline.",
                occurred_at=now - timedelta(days=index + 1),
                created_by=user,
            )
        Contact.objects.create(
            organization=organization,
            first_name="Alex",
            last_name="Rivera",
            email="alex.rivera@example.org",
            external_ref="SAMPLE-DUPLICATE",
            notes="Synthetic duplicate for trying the reviewed merge workflow.",
        )
        program = Program.objects.create(
            organization=organization,
            name="Community pantry",
            description="A fictional programme for hands-on training.",
        )
        for index, title in enumerate(
            [
                "Community pantry · morning shift",
                "Volunteer welcome session",
                "Community garden planning",
            ]
        ):
            ScheduleEvent.objects.create(
                organization=organization,
                title=title,
                event_type="shift" if index == 0 else "meeting",
                starts_at=now + timedelta(days=index + 1),
                ends_at=now + timedelta(days=index + 1, hours=2),
                location="Sample community centre",
                program=program,
                notes="Fictional event. No invitations or reminders are sent.",
            )
        for name, email, skills in [
            ("Alex Rivera", "alex.rivera@example.org", ["Food preparation", "Driving"]),
            ("Sam Chen", "sam.chen@example.org", ["Reception", "Translation"]),
        ]:
            VolunteerApplication.objects.create(
                organization=organization,
                applicant_name=name,
                email=email,
                skills=skills,
                interests=["Community support"],
                notes="Synthetic training application, not a real applicant.",
            )
        GrantWorkspace.objects.create(
            organization=organization,
            name="Community connections · sample grant",
            funder="Fictional Community Fund",
            deadline=(now + timedelta(days=45)).date(),
            organizational_profile="Fictional charity providing a pantry and volunteer-led community activities.",
        )
        CommunityResource.objects.create(
            organization=organization,
            name="Sample community pantry",
            category="Food support",
            description="Fictional directory entry for trying search and editing. Not a real service.",
            languages=["English", "French"],
            accessibility=["Step-free entrance"],
            address="Sample address · do not use for directions",
            source_url="https://example.org",
        )
        MetricDefinition.objects.create(
            organization=organization,
            key="volunteer_hours",
            name="Volunteer hours",
            definition="Approved attendance hours. Sample workspace starts without real activity.",
            unit="hours",
            owner=user,
        )
        self.stdout.write("Synthetic showcase workspace prepared.")
