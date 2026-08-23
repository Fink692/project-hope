from django.core.exceptions import PermissionDenied
from django.conf import settings
from rest_framework.permissions import BasePermission

from .models import Membership, MultiFactorCredential


ADMIN_ROLES = {Membership.Role.OWNER, Membership.Role.ADMIN}
EDITOR_ROLES = {
    Membership.Role.OWNER,
    Membership.Role.ADMIN,
    Membership.Role.COORDINATOR,
    Membership.Role.STAFF,
}


class IsAuthenticatedAndMfaCompliant(BasePermission):
    """Require authentication and the deployment's MFA enrollment policy."""

    message = "Set up two-step verification before opening organization data."

    def has_permission(self, request, view):
        user = request.user
        if not user or not user.is_authenticated or not user.is_active:
            return False
        if not settings.PROJECT_HOPE_MFA_REQUIRED:
            return True
        return MultiFactorCredential.objects.filter(user=user).exists()


class IsAdminAndMfaCompliant(IsAuthenticatedAndMfaCompliant):
    message = "Administrator access with two-step verification is required."

    def has_permission(self, request, view):
        return super().has_permission(request, view) and bool(request.user.is_staff)


def active_membership(user, organization):
    if not user or not user.is_authenticated:
        return None
    return (
        Membership.objects.select_related("organization", "user")
        .filter(user=user, organization=organization, active=True)
        .first()
    )


def require_membership(user, organization):
    membership = active_membership(user, organization)
    if membership is None:
        raise PermissionDenied("You are not an active member of this organization.")
    return membership


def require_admin(membership):
    if membership.role not in ADMIN_ROLES:
        raise PermissionDenied("Owner or administrator role required.")
    return membership


def require_editor(membership):
    if membership.role not in EDITOR_ROLES:
        raise PermissionDenied("A role with record-editing access is required.")
    return membership


def require_owner(membership):
    if membership.role != Membership.Role.OWNER:
        raise PermissionDenied("Owner role required.")
    return membership
