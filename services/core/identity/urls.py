from django.urls import path

from .views import (
    AuditEventListView,
    CsrfView,
    InvitationAcceptView,
    InvitationInspectView,
    LoginView,
    LogoutView,
    MeView,
    MembershipDetailView,
    MembershipListView,
    OrganizationDetailView,
    OrganizationInvitationDetailView,
    OrganizationInvitationListCreateView,
    OrganizationInvitationResendView,
    PasswordResetConfirmView,
    PasswordResetInspectView,
    PasswordResetRequestView,
    OrganizationListCreateView,
    PilotApplicationView,
    PilotMetricsView,
    PilotVerificationView,
    TokenLoginView,
)


urlpatterns = [
    path("auth/csrf/", CsrfView.as_view(), name="auth-csrf"),
    path("auth/login/", LoginView.as_view(), name="auth-login"),
    path("auth/token/", TokenLoginView.as_view(), name="auth-token"),
    path("auth/logout/", LogoutView.as_view(), name="auth-logout"),
    path(
        "auth/password-reset/",
        PasswordResetRequestView.as_view(),
        name="password-reset-request",
    ),
    path(
        "auth/password-reset/inspect/",
        PasswordResetInspectView.as_view(),
        name="password-reset-inspect",
    ),
    path(
        "auth/password-reset/confirm/",
        PasswordResetConfirmView.as_view(),
        name="password-reset-confirm",
    ),
    path(
        "invitations/inspect/",
        InvitationInspectView.as_view(),
        name="invitation-inspect",
    ),
    path(
        "invitations/accept/",
        InvitationAcceptView.as_view(),
        name="invitation-accept",
    ),
    path("me/", MeView.as_view(), name="me"),
    path(
        "pilot-applications/",
        PilotApplicationView.as_view(),
        name="pilot-application",
    ),
    path(
        "pilot-applications/verify/",
        PilotVerificationView.as_view(),
        name="pilot-verification",
    ),
    path(
        "pilot-applications/metrics/",
        PilotMetricsView.as_view(),
        name="pilot-metrics",
    ),
    path(
        "organizations/",
        OrganizationListCreateView.as_view(),
        name="organization-list-create",
    ),
    path(
        "organizations/<slug:slug>/",
        OrganizationDetailView.as_view(),
        name="organization-detail",
    ),
    path(
        "organizations/<slug:slug>/members/",
        MembershipListView.as_view(),
        name="membership-list",
    ),
    path(
        "organizations/<slug:slug>/invitations/",
        OrganizationInvitationListCreateView.as_view(),
        name="organization-invitation-list-create",
    ),
    path(
        "organizations/<slug:slug>/invitations/<uuid:invitation_id>/",
        OrganizationInvitationDetailView.as_view(),
        name="organization-invitation-detail",
    ),
    path(
        "organizations/<slug:slug>/invitations/<uuid:invitation_id>/resend/",
        OrganizationInvitationResendView.as_view(),
        name="organization-invitation-resend",
    ),
    path(
        "organizations/<slug:slug>/members/<uuid:membership_id>/",
        MembershipDetailView.as_view(),
        name="membership-detail",
    ),
    path(
        "organizations/<slug:slug>/audit-events/",
        AuditEventListView.as_view(),
        name="audit-events",
    ),
]
