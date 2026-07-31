from django.contrib import admin

from . import models


class TenantRecordAdmin(admin.ModelAdmin):
    """Safe operational view for tenant records.

    Destructive retention actions are intentionally handled by the audited
    ``run_retention`` command rather than an accidental admin click.
    """

    list_display = ("organization", "created_at", "updated_at")
    list_filter = ("organization",)
    search_fields = ("organization__name",)
    ordering = ("-updated_at",)
    readonly_fields = ("id", "created_at", "updated_at")

    def has_delete_permission(self, request, obj=None):
        return False


_TENANT_MODELS = (
    models.Contact,
    models.Household,
    models.ContactRelationship,
    models.Interaction,
    models.ConsentRecord,
    models.Program,
    models.VolunteerProfile,
    models.VolunteerApplication,
    models.ScheduleEvent,
    models.WaitlistEntry,
    models.DocumentRecord,
    models.DocumentPassage,
    models.Workflow,
    models.WorkflowReview,
    models.AIModelRegistry,
    models.Mailbox,
    models.EmailMessage,
    models.EmailDraft,
    models.MetricDefinition,
    models.MetricSnapshot,
    models.GrantWorkspace,
    models.GrantQuestion,
    models.CommunityResource,
    models.TranslationJob,
    models.TranslationMemory,
    models.AccessibilityTransform,
    models.VoiceCall,
    models.DonorSnapshot,
    models.PluginPackage,
    models.PluginInstallation,
    models.PluginCapabilityToken,
    models.PublicAPIClient,
    models.RetentionPolicy,
)

admin.site.register(_TENANT_MODELS, TenantRecordAdmin)
