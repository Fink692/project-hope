from django.urls import path

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
from .views import (
    APIClientIssueView,
    AIOperationView,
    DocumentSearchView,
    DonorCohortView,
    EmailApprovalView,
    EmailSendView,
    MetricSummaryView,
    PluginInstallView,
    PluginTokenIssueView,
    PluginRevokeView,
    PublicResourceAPIView,
    ResourceSearchView,
    ResourceVerifyView,
    ScheduleICSView,
    AccessibilityReviewView,
    GrantBudgetValidationView,
    TranslationReviewView,
    VoiceActionView,
    VolunteerApplicationReviewView,
    VolunteerPipelineView,
    WorkflowReviewView,
    ADMIN_ONLY_MODELS,
    build_resource_views,
)


RESOURCE_ROUTES = {
    "contacts": Contact,
    "households": Household,
    "relationships": ContactRelationship,
    "interactions": Interaction,
    "consents": ConsentRecord,
    "programs": Program,
    "volunteer-profiles": VolunteerProfile,
    "volunteer-applications": VolunteerApplication,
    "schedules": ScheduleEvent,
    "waitlist": WaitlistEntry,
    "documents": DocumentRecord,
    "passages": DocumentPassage,
    "workflows": Workflow,
    "workflow-reviews": WorkflowReview,
    "ai-models": AIModelRegistry,
    "mailboxes": Mailbox,
    "messages": EmailMessage,
    "email-drafts": EmailDraft,
    "metrics": MetricDefinition,
    "metric-snapshots": MetricSnapshot,
    "grants": GrantWorkspace,
    "grant-questions": GrantQuestion,
    "resources": CommunityResource,
    "translations": TranslationJob,
    "translation-memory": TranslationMemory,
    "accessibility-transforms": AccessibilityTransform,
    "calls": VoiceCall,
    "donor-snapshots": DonorSnapshot,
    "plugins": PluginPackage,
    "plugin-installations": PluginInstallation,
    "plugin-capability-tokens": PluginCapabilityToken,
    "api-clients": PublicAPIClient,
    "retention-policies": RetentionPolicy,
}

urlpatterns = []
for route, model in RESOURCE_ROUTES.items():
    list_view, detail_view = build_resource_views(
        model, admin_only=model in ADMIN_ONLY_MODELS
    )
    urlpatterns.extend(
        [
            path(
                f"organizations/<slug:slug>/{route}/",
                list_view,
                name=f"{route}-list-create",
            ),
            path(
                f"organizations/<slug:slug>/{route}/<uuid:pk>/",
                detail_view,
                name=f"{route}-detail",
            ),
        ]
    )

urlpatterns.extend(
    [
        path(
            "organizations/<slug:slug>/documents/search/",
            DocumentSearchView.as_view(),
            name="document-search",
        ),
        path(
            "organizations/<slug:slug>/resources/search/",
            ResourceSearchView.as_view(),
            name="resource-search",
        ),
        path(
            "organizations/<slug:slug>/resources/<uuid:pk>/verify/",
            ResourceVerifyView.as_view(),
            name="resource-verify",
        ),
        path(
            "organizations/<slug:slug>/schedules/ical/",
            ScheduleICSView.as_view(),
            name="schedule-ical",
        ),
        path(
            "organizations/<slug:slug>/metrics/summary/",
            MetricSummaryView.as_view(),
            name="metric-summary",
        ),
        path(
            "organizations/<slug:slug>/grants/<uuid:pk>/validate-budget/",
            GrantBudgetValidationView.as_view(),
            name="grant-budget-validation",
        ),
        path(
            "organizations/<slug:slug>/translations/<uuid:pk>/review/",
            TranslationReviewView.as_view(),
            name="translation-review",
        ),
        path(
            "organizations/<slug:slug>/accessibility-transforms/<uuid:pk>/review/",
            AccessibilityReviewView.as_view(),
            name="accessibility-review",
        ),
        path(
            "organizations/<slug:slug>/volunteers/pipeline/",
            VolunteerPipelineView.as_view(),
            name="volunteer-pipeline",
        ),
        path(
            "organizations/<slug:slug>/volunteer-applications/<uuid:pk>/review/",
            VolunteerApplicationReviewView.as_view(),
            name="volunteer-application-review",
        ),
        path(
            "organizations/<slug:slug>/workflows/<uuid:pk>/review/",
            WorkflowReviewView.as_view(),
            name="workflow-review",
        ),
        path(
            "organizations/<slug:slug>/email-drafts/<uuid:pk>/approval/",
            EmailApprovalView.as_view(),
            name="email-approval",
        ),
        path(
            "organizations/<slug:slug>/email-drafts/<uuid:pk>/send/",
            EmailSendView.as_view(),
            name="email-send",
        ),
        path(
            "organizations/<slug:slug>/ai/v1/<slug:operation>/",
            AIOperationView.as_view(),
            name="ai-operation",
        ),
        path(
            "organizations/<slug:slug>/donors/cohort/",
            DonorCohortView.as_view(),
            name="donor-cohort",
        ),
        path(
            "organizations/<slug:slug>/calls/<uuid:pk>/action/",
            VoiceActionView.as_view(),
            name="voice-action",
        ),
        path(
            "organizations/<slug:slug>/plugins/<uuid:pk>/install/",
            PluginInstallView.as_view(),
            name="plugin-install",
        ),
        path(
            "organizations/<slug:slug>/plugins/<uuid:pk>/revoke/",
            PluginRevokeView.as_view(),
            name="plugin-revoke",
        ),
        path(
            "organizations/<slug:slug>/plugin-installations/<uuid:pk>/token/",
            PluginTokenIssueView.as_view(),
            name="plugin-token-issue",
        ),
        path(
            "organizations/<slug:slug>/developer/api-clients/issue/",
            APIClientIssueView.as_view(),
            name="api-client-issue",
        ),
        path(
            "public/v1/resources/",
            PublicResourceAPIView.as_view(),
            name="public-resource-search",
        ),
    ]
)
