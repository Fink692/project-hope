from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from .models import (
    Membership,
    Organization,
    OrganizationInvitation,
    PasswordResetDelivery,
    PilotApplication,
    User,
)


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    ordering = ["email"]
    list_display = ("email", "first_name", "last_name", "is_staff", "is_active")
    search_fields = ("email", "first_name", "last_name")
    fieldsets = (
        (None, {"fields": ("email", "password")}),
        ("Personal info", {"fields": ("first_name", "last_name")}),
        (
            "Permissions",
            {
                "fields": (
                    "is_active",
                    "is_staff",
                    "is_superuser",
                    "groups",
                    "user_permissions",
                )
            },
        ),
        ("Important dates", {"fields": ("last_login", "date_joined")}),
    )
    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": ("email", "password1", "password2", "is_active", "is_staff"),
            },
        ),
    )


@admin.register(Organization)
class OrganizationAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "status", "created_at")
    search_fields = ("name", "slug")
    list_filter = ("status",)


@admin.register(Membership)
class MembershipAdmin(admin.ModelAdmin):
    list_display = ("organization", "user", "role", "active", "created_at")
    search_fields = ("organization__name", "user__email")
    list_filter = ("role", "active")


@admin.register(OrganizationInvitation)
class OrganizationInvitationAdmin(admin.ModelAdmin):
    list_display = (
        "email",
        "organization",
        "role",
        "status",
        "expires_at",
        "email_sent_at",
        "created_at",
    )
    list_filter = ("status", "role")
    search_fields = ("email", "organization__name")
    readonly_fields = (
        "id",
        "token_version",
        "email_sent_at",
        "email_last_attempt_at",
        "email_attempts",
        "accepted_at",
        "revoked_at",
        "created_at",
        "updated_at",
    )


@admin.register(PasswordResetDelivery)
class PasswordResetDeliveryAdmin(admin.ModelAdmin):
    list_display = (
        "user",
        "status",
        "email_attempts",
        "email_sent_at",
        "expires_at",
        "created_at",
    )
    list_filter = ("status",)
    search_fields = ("user__email",)
    exclude = ("password_fingerprint",)
    readonly_fields = (
        "id",
        "user",
        "status",
        "expires_at",
        "email_sent_at",
        "email_last_attempt_at",
        "email_attempts",
        "created_at",
        "updated_at",
    )

    def has_add_permission(self, request):
        return False


@admin.register(PilotApplication)
class PilotApplicationAdmin(admin.ModelAdmin):
    list_display = (
        "organization_name",
        "contact_name",
        "email",
        "plan_interest",
        "status",
        "is_verified",
        "email_delivered",
        "created_at",
    )
    list_filter = (
        "status",
        "plan_interest",
        "primary_need",
        "team_size",
        "source",
        "consent_to_contact",
    )
    search_fields = ("organization_name", "contact_name", "email")
    readonly_fields = (
        "id",
        "email",
        "verified_at",
        "verification_email_sent_at",
        "verification_email_last_attempt_at",
        "verification_email_attempts",
        "privacy_version",
        "submission_count",
        "created_at",
        "updated_at",
    )
    date_hierarchy = "created_at"

    @admin.display(boolean=True, description="Verified")
    def is_verified(self, application):
        return application.verified_at is not None

    @admin.display(boolean=True, description="Email delivered")
    def email_delivered(self, application):
        return application.verification_email_sent_at is not None
