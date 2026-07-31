from django.core.exceptions import PermissionDenied

from .models import Membership


ADMIN_ROLES = {Membership.Role.OWNER, Membership.Role.ADMIN}


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


def require_owner(membership):
    if membership.role != Membership.Role.OWNER:
        raise PermissionDenied("Owner role required.")
    return membership
