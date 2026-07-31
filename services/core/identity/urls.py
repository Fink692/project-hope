from django.urls import path

from .views import (
    AuditEventListView,
    CsrfView,
    LoginView,
    LogoutView,
    MeView,
    MembershipDetailView,
    MembershipListView,
    OrganizationDetailView,
    OrganizationListCreateView,
)


urlpatterns = [
    path("auth/csrf/", CsrfView.as_view(), name="auth-csrf"),
    path("auth/login/", LoginView.as_view(), name="auth-login"),
    path("auth/logout/", LogoutView.as_view(), name="auth-logout"),
    path("me/", MeView.as_view(), name="me"),
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
