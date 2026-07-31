import json

from django.core.management.base import BaseCommand, CommandError
from django.forms.models import model_to_dict

from audit.models import AuditEvent
from identity.models import Membership, Organization
from modules.models import TenantRecord


class Command(BaseCommand):
    help = "Export tenant-owned relational records and audit metadata to a JSON file."

    def add_arguments(self, parser):
        parser.add_argument("organization")
        parser.add_argument("output")

    def handle(self, *args, **options):
        try:
            organization = Organization.objects.get(slug=options["organization"])
        except Organization.DoesNotExist as exc:
            raise CommandError("Organization not found.") from exc
        payload = {
            "organization": {
                "id": str(organization.id),
                "name": organization.name,
                "slug": organization.slug,
            },
            "memberships": [
                {
                    "id": str(member.id),
                    "email": member.user.email,
                    "role": member.role,
                    "active": member.active,
                }
                for member in Membership.objects.filter(
                    organization=organization
                ).select_related("user")
            ],
            "records": {},
            "auditEvents": [
                {
                    "id": str(event.id),
                    "action": event.action,
                    "eventType": event.event_type,
                    "resourceType": event.resource_type,
                    "resourceId": event.resource_id,
                    "metadata": event.metadata,
                    "createdAt": event.created_at.isoformat(),
                }
                for event in AuditEvent.objects.filter(organization=organization)
            ],
        }
        for model in TenantRecord.__subclasses__():
            records = model.objects.filter(organization=organization)
            payload["records"][model.__name__] = []
            for record in records:
                data = model_to_dict(record)
                data["id"] = str(record.id)
                data["organization"] = str(organization.id)
                for key, value in list(data.items()):
                    if hasattr(value, "isoformat"):
                        data[key] = value.isoformat()
                    elif (
                        isinstance(value, (list, dict, str, int, float, bool))
                        or value is None
                    ):
                        continue
                    else:
                        data[key] = str(value)
                payload["records"][model.__name__].append(data)
        with open(options["output"], "w", encoding="utf-8") as handle:
            json.dump(payload, handle, indent=2, default=str)
        self.stdout.write(
            self.style.SUCCESS(f"Exported {organization.slug} to {options['output']}")
        )
