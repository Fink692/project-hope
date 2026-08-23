from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from audit.models import AuditEvent
from identity.mfa import (
    MfaSecretUnavailable,
    current_encryption_key_id,
    rotate_encrypted_secret,
)
from identity.models import MultiFactorCredential


class Command(BaseCommand):
    help = "Validate or re-encrypt every TOTP secret with the first configured MFA key."

    def add_arguments(self, parser):
        parser.add_argument(
            "--execute",
            action="store_true",
            help="Write rotated ciphertext after every credential validates.",
        )

    def handle(self, *args, **options):
        execute = bool(options["execute"])
        primary_key_id = current_encryption_key_id()
        rotated = 0
        legacy_recovery_sets = 0
        try:
            with transaction.atomic():
                credentials = list(
                    MultiFactorCredential.objects.select_for_update().order_by("id")
                )
                rotated_values = []
                for credential in credentials:
                    rotated_values.append(
                        (
                            credential,
                            rotate_encrypted_secret(credential.encrypted_secret),
                        )
                    )
                    if (
                        credential.recovery_code_hashes
                        and credential.recovery_key_id != primary_key_id
                    ):
                        legacy_recovery_sets += 1
                if execute:
                    for credential, encrypted_secret in rotated_values:
                        credential.encrypted_secret = encrypted_secret
                        credential.save(
                            update_fields=["encrypted_secret", "updated_at"]
                        )
                        AuditEvent.objects.record(
                            action="auth.mfa_secret_reencrypted",
                            event_type="authentication",
                            resource_type="multi_factor_credential",
                            resource_id=credential.id,
                            metadata={"primary_key_id": primary_key_id},
                        )
                        rotated += 1
                else:
                    transaction.set_rollback(True)
        except MfaSecretUnavailable as exc:
            raise CommandError(
                "At least one MFA secret cannot be decrypted with the configured keys; "
                "no credentials were changed."
            ) from exc

        action = "re-encrypted" if execute else "validated"
        self.stdout.write(
            self.style.SUCCESS(
                f"{len(credentials)} MFA credential(s) {action}; "
                f"{rotated} ciphertext value(s) written."
            )
        )
        if legacy_recovery_sets:
            self.stdout.write(
                self.style.WARNING(
                    f"{legacy_recovery_sets} recovery-code set(s) still require an "
                    "older key. Keep prior keys configured until those users regenerate "
                    "their recovery codes or MFA is reset."
                )
            )
