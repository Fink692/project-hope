import json

from django.core.exceptions import ValidationError
from django.core.management.base import BaseCommand, CommandError
from django.core.validators import validate_email
from django.utils.text import slugify

from audit.models import AuditEvent
from identity.invitations import prepare_team_invitation, send_team_invitation
from identity.models import Membership, Organization, User


class Command(BaseCommand):
    help = "Create a production organization and email its first owner invitation."

    def add_arguments(self, parser):
        parser.add_argument("--organization", required=True)
        parser.add_argument("--owner-email", required=True)
        parser.add_argument("--slug")

    def handle(self, *args, **options):
        name = options["organization"].strip()
        email = options["owner_email"].strip().lower()
        slug = (options.get("slug") or slugify(name)).strip()
        if not name or not slug:
            raise CommandError("Organization name and slug cannot be empty.")
        try:
            validate_email(email)
        except ValidationError as exc:
            raise CommandError("Enter a valid owner email address.") from exc

        organization, organization_created = Organization.objects.get_or_create(
            slug=slug,
            defaults={"name": name},
        )
        if not organization_created and organization.name != name:
            raise CommandError(
                f"The slug '{slug}' already belongs to '{organization.name}'. "
                "Choose a different --slug."
            )
        if organization.status != Organization.Status.ACTIVE:
            raise CommandError("The matching organization is archived.")

        user = User.objects.filter(email__iexact=email, is_active=True).first()
        if user is not None:
            membership = Membership.objects.filter(
                organization=organization, user=user, active=True
            ).first()
            if membership is not None:
                changed = membership.role != Membership.Role.OWNER
                if changed:
                    membership.role = Membership.Role.OWNER
                    membership.save(update_fields=["role", "updated_at"])
                    AuditEvent.objects.record(
                        action="membership.promoted_to_owner",
                        actor=user,
                        organization=organization,
                        event_type="authorization",
                        resource_type="membership",
                        resource_id=membership.id,
                        metadata={"source": "bootstrap_workspace"},
                    )
                self.stdout.write(
                    json.dumps(
                        {
                            "delivery": "not_needed",
                            "organization": organization.slug,
                            "owner": "ready",
                        },
                        sort_keys=True,
                    )
                )
                return

        invitation, invitation_created = prepare_team_invitation(
            organization=organization,
            email=email,
            role=Membership.Role.OWNER,
        )
        delivered = send_team_invitation(invitation)
        invitation.refresh_from_db()
        AuditEvent.objects.record(
            action=(
                "workspace.bootstrap_invitation.created"
                if invitation_created
                else "workspace.bootstrap_invitation.refreshed"
            ),
            organization=organization,
            event_type="authorization",
            resource_type="organization_invitation",
            resource_id=invitation.id,
            metadata={"email_delivered": delivered},
        )
        self.stdout.write(
            json.dumps(
                {
                    "delivery": "sent" if delivered else "retrying",
                    "organization": organization.slug,
                    "owner": "invited",
                },
                sort_keys=True,
            )
        )
