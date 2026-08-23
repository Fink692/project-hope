from django.core.mail import EmailMessage
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from audit.models import AuditEvent
from identity.mfa import MfaNotEnabled, reset_mfa_by_operator
from identity.models import User


class Command(BaseCommand):
    help = "Reset one user's MFA after an operator completes account recovery checks."

    def add_arguments(self, parser):
        parser.add_argument("--email", required=True)
        parser.add_argument("--confirm-email", required=True)
        parser.add_argument("--reason", required=True)

    def handle(self, *args, **options):
        email = options["email"].strip().lower()
        confirmation = options["confirm_email"].strip().lower()
        reason = options["reason"].strip()
        if email != confirmation:
            raise CommandError("--confirm-email must exactly match --email.")
        if not reason or len(reason) > 200:
            raise CommandError("--reason must contain 1 to 200 characters.")
        try:
            user = User.objects.get(email__iexact=email, is_active=True)
        except User.DoesNotExist as exc:
            raise CommandError("No active user matches that email.") from exc

        try:
            with transaction.atomic():
                credential = reset_mfa_by_operator(user)
                AuditEvent.objects.record(
                    action="auth.mfa_reset_by_operator",
                    event_type="authentication",
                    resource_type="multi_factor_credential",
                    resource_id=credential.id,
                    metadata={"reason": reason},
                )
        except MfaNotEnabled as exc:
            raise CommandError(
                "Two-step verification is not enabled for this user."
            ) from exc

        try:
            EmailMessage(
                subject="Project Hope two-step verification was reset",
                body=(
                    "A Project Hope operator reset two-step verification for "
                    "your account after an account-recovery request. All existing "
                    "sessions and native access tokens are no longer valid. Sign in "
                    "and set up two-step verification again before opening your "
                    "workspace. If you did not request this, contact your Project "
                    "Hope operator immediately."
                ),
                to=[user.email],
            ).send(fail_silently=False)
        except Exception as exc:
            raise CommandError(
                "Two-step verification was reset, but the security notification "
                "failed. Contact the user through an approved channel immediately."
            ) from exc

        self.stdout.write(
            self.style.SUCCESS(
                "Two-step verification reset; notification accepted for delivery."
            )
        )
