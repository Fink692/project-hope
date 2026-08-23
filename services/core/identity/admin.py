from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from .models import Membership, Organization, PilotApplication, User


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
