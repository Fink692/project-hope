from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from audit.models import AuditEvent

from modules.models import (
    AccessibilityTransform,
    CommunityResource,
    Contact,
    DocumentRecord,
    EmailMessage,
    TranslationJob,
    VoiceCall,
    Workflow,
    RetentionPolicy,
    TenantRecord,
)


RETENTION_MODELS = {
    "contacts": Contact,
    "documents": DocumentRecord,
    "email_messages": EmailMessage,
    "voice_calls": VoiceCall,
    "workflows": Workflow,
    "translations": TranslationJob,
    "accessibility_transforms": AccessibilityTransform,
    "resources": CommunityResource,
}
for tenant_model in TenantRecord.__subclasses__():
    if tenant_model is not RetentionPolicy:
        RETENTION_MODELS.setdefault(tenant_model._meta.model_name, tenant_model)
        RETENTION_MODELS.setdefault(f"{tenant_model._meta.model_name}s", tenant_model)


class Command(BaseCommand):
    help = "Preview or execute organization retention policies. Deletion requires --execute."

    def add_arguments(self, parser):
        parser.add_argument("--execute", action="store_true")
        parser.add_argument("--organization", default="")

    def handle(self, *args, **options):
        policies = RetentionPolicy.objects.filter(
            enabled=True, legal_hold=False
        ).select_related("organization")
        if options["organization"]:
            policies = policies.filter(organization__slug=options["organization"])
        for policy in policies:
            model = RETENTION_MODELS.get(policy.record_type)
            if model is None:
                self.stderr.write(f"unsupported record type: {policy.record_type}")
                continue
            cutoff = timezone.now() - timedelta(days=policy.retention_days)
            queryset = model.objects.filter(
                organization=policy.organization, created_at__lt=cutoff
            )
            count = queryset.count()
            if not options["execute"]:
                self.stdout.write(
                    f"preview {policy.organization.slug}/{policy.record_type}: {count}"
                )
                continue
            for instance in queryset.iterator():
                identifier = str(instance.id)
                if isinstance(instance, DocumentRecord) and instance.file:
                    instance.file.delete(save=False)
                instance.delete()
                AuditEvent.objects.record(
                    action="retention.deleted",
                    organization=policy.organization,
                    event_type="privacy",
                    resource_type=policy.record_type,
                    resource_id=identifier,
                    metadata={"retentionDays": policy.retention_days},
                )
            policy.last_run_at = timezone.now()
            policy.save(update_fields=["last_run_at", "updated_at"])
            self.stdout.write(
                self.style.SUCCESS(
                    f"deleted {policy.organization.slug}/{policy.record_type}: {count}"
                )
            )
