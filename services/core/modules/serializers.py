from django.contrib.auth import get_user_model
from rest_framework import serializers

from .models import (
    AccessibilityTransform,
    AIModelRegistry,
    CommunityResource,
    ConsentRecord,
    Contact,
    ContactRelationship,
    DocumentPassage,
    DocumentRecord,
    DonorSnapshot,
    EmailDraft,
    EmailMessage,
    GrantQuestion,
    GrantWorkspace,
    Household,
    Interaction,
    Mailbox,
    MetricDefinition,
    MetricSnapshot,
    PluginCapabilityToken,
    PluginInstallation,
    PluginPackage,
    Program,
    PublicAPIClient,
    RetentionPolicy,
    ScheduleEvent,
    TranslationJob,
    TranslationMemory,
    VoiceCall,
    VolunteerApplication,
    VolunteerProfile,
    WaitlistEntry,
    Workflow,
    WorkflowReview,
)

User = get_user_model()


class TenantModelSerializer(serializers.ModelSerializer):
    """Shared serializer policy for tenant-owned records.

    Related tenant records are checked against the organization in the request
    context before a write. This prevents a valid UUID from another tenant from
    being smuggled into a relationship field.
    """

    def validate(self, attrs):
        organization = self.context.get("organization")
        if organization is not None:
            for field in self.Meta.model._meta.fields:
                if not field.is_relation or field.name == "organization":
                    continue
                related = attrs.get(field.name)
                if related is not None and hasattr(related, "organization_id"):
                    if related.organization_id != organization.id:
                        raise serializers.ValidationError(
                            {
                                field.name: "Related records must belong to the same organization."
                            }
                        )
        return attrs


def fields_for(model):
    return [field.name for field in model._meta.fields]


def readonly_for(model):
    readonly = {"id", "organization", "created_at", "updated_at"}
    for field in model._meta.fields:
        if field.is_relation and field.related_model is User:
            readonly.add(field.name)
    return list(readonly)


def build_serializer(model):
    class GeneratedTenantSerializer(TenantModelSerializer):
        class Meta:
            pass

    GeneratedTenantSerializer.Meta.model = model
    GeneratedTenantSerializer.Meta.fields = fields_for(model)
    GeneratedTenantSerializer.Meta.read_only_fields = readonly_for(model)
    if model is Contact:
        GeneratedTenantSerializer._declared_fields["display_name"] = (
            serializers.CharField(read_only=True)
        )
        GeneratedTenantSerializer.Meta.fields = [
            *GeneratedTenantSerializer.Meta.fields,
            "display_name",
        ]

    GeneratedTenantSerializer.__name__ = f"{model.__name__}Serializer"
    return GeneratedTenantSerializer


MODEL_SERIALIZERS = {
    model: build_serializer(model)
    for model in [
        AccessibilityTransform,
        AIModelRegistry,
        CommunityResource,
        ConsentRecord,
        Contact,
        ContactRelationship,
        DocumentPassage,
        DocumentRecord,
        DonorSnapshot,
        EmailDraft,
        EmailMessage,
        GrantQuestion,
        GrantWorkspace,
        Household,
        Interaction,
        Mailbox,
        MetricDefinition,
        MetricSnapshot,
        PluginCapabilityToken,
        PluginInstallation,
        PluginPackage,
        Program,
        PublicAPIClient,
        RetentionPolicy,
        ScheduleEvent,
        TranslationJob,
        TranslationMemory,
        VoiceCall,
        VolunteerApplication,
        VolunteerProfile,
        WaitlistEntry,
        Workflow,
        WorkflowReview,
    ]
}


class OrganizationScopedInputSerializer(serializers.Serializer):
    text = serializers.CharField(required=False, allow_blank=True)
