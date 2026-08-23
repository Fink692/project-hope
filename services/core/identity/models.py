import uuid

from django.contrib.auth.base_user import BaseUserManager
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin
from django.db import models


class UserManager(BaseUserManager):
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError("An email address is required.")
        user = self.model(email=self.normalize_email(email), **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("is_active", True)
        if extra_fields.get("is_staff") is not True:
            raise ValueError("Superuser must have is_staff=True.")
        if extra_fields.get("is_superuser") is not True:
            raise ValueError("Superuser must have is_superuser=True.")
        return self.create_user(email, password, **extra_fields)


class User(AbstractBaseUser, PermissionsMixin):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    email = models.EmailField(unique=True)
    first_name = models.CharField(max_length=150, blank=True)
    last_name = models.CharField(max_length=150, blank=True)
    is_staff = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    date_joined = models.DateTimeField(auto_now_add=True)

    objects = UserManager()

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS: list[str] = []

    def __str__(self):
        return self.email

    @property
    def display_name(self):
        name = f"{self.first_name} {self.last_name}".strip()
        return name or self.email


class Organization(models.Model):
    class Status(models.TextChoices):
        ACTIVE = "active", "Active"
        ARCHIVED = "archived", "Archived"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=200)
    slug = models.SlugField(max_length=220, unique=True)
    status = models.CharField(
        max_length=16, choices=Status.choices, default=Status.ACTIVE
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class Membership(models.Model):
    class Role(models.TextChoices):
        OWNER = "owner", "Owner"
        ADMIN = "admin", "Administrator"
        COORDINATOR = "coordinator", "Coordinator"
        STAFF = "staff", "Staff"
        VIEWER = "viewer", "Viewer"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey(
        Organization, on_delete=models.CASCADE, related_name="memberships"
    )
    user = models.ForeignKey(
        "User", on_delete=models.CASCADE, related_name="memberships"
    )
    role = models.CharField(max_length=24, choices=Role.choices, default=Role.VIEWER)
    active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["organization", "user"], name="unique_org_user_membership"
            ),
        ]
        ordering = ["user__email"]

    def __str__(self):
        return f"{self.user.email} @ {self.organization.slug} ({self.role})"


class PilotApplication(models.Model):
    """A privacy-minimized request to join the Founding 10 programme."""

    PRIVACY_VERSION = "2026-08-23"

    class Status(models.TextChoices):
        NEW = "new", "New"
        CONTACTED = "contacted", "Contacted"
        QUALIFIED = "qualified", "Qualified"
        PILOT = "pilot", "Pilot active"
        CONVERTED = "converted", "Converted"
        DECLINED = "declined", "Declined"

    class TeamSize(models.TextChoices):
        ONE = "1", "1 person"
        TWO_TO_FIVE = "2-5", "2–5 people"
        SIX_TO_TWENTY = "6-20", "6–20 people"
        TWENTY_ONE_TO_FIFTY = "21-50", "21–50 people"
        FIFTY_ONE_PLUS = "51+", "51+ people"

    class PrimaryNeed(models.TextChoices):
        OPERATIONS = "operations", "Operations in one place"
        VOLUNTEERS = "volunteers", "Volunteer coordination"
        GRANTS = "grants", "Grants and evidence"
        COMMUNICATIONS = "communications", "Safer communications"
        IMPACT = "impact", "Impact and reporting"
        ACCESSIBILITY = "accessibility", "Accessibility and translation"
        OTHER = "other", "Something else"

    class PlanInterest(models.TextChoices):
        COMMUNITY = "community", "Community — self-hosted"
        FOUNDING_PARTNER = "founding_partner", "Founding Partner — managed support"
        NETWORK = "network", "Partner Network — multiple charities"

    class Source(models.TextChoices):
        WEBSITE = "website", "Website"
        LINKEDIN = "linkedin", "LinkedIn"
        PARTNER = "partner", "Partner"
        REFERRAL = "referral", "Referral"
        DIRECT = "direct", "Direct"
        OTHER = "other", "Other"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    contact_name = models.CharField(max_length=160)
    email = models.EmailField(unique=True)
    organization_name = models.CharField(max_length=200)
    website = models.URLField(max_length=500, blank=True)
    country_or_region = models.CharField(max_length=120, blank=True)
    team_size = models.CharField(max_length=12, choices=TeamSize.choices)
    primary_need = models.CharField(max_length=32, choices=PrimaryNeed.choices)
    plan_interest = models.CharField(max_length=32, choices=PlanInterest.choices)
    notes = models.TextField(blank=True)
    consent_to_contact = models.BooleanField(default=False)
    privacy_version = models.CharField(max_length=20, default=PRIVACY_VERSION)
    source = models.CharField(
        max_length=24, choices=Source.choices, default=Source.WEBSITE
    )
    utm_source = models.CharField(max_length=120, blank=True)
    utm_medium = models.CharField(max_length=120, blank=True)
    utm_campaign = models.CharField(max_length=160, blank=True)
    referrer = models.URLField(max_length=500, blank=True)
    status = models.CharField(max_length=24, choices=Status.choices, default=Status.NEW)
    verified_at = models.DateTimeField(null=True, blank=True)
    verification_email_sent_at = models.DateTimeField(null=True, blank=True)
    verification_email_last_attempt_at = models.DateTimeField(null=True, blank=True)
    verification_email_attempts = models.PositiveIntegerField(default=0)
    submission_count = models.PositiveIntegerField(default=1)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def save(self, *args, **kwargs):
        self.email = self.email.strip().lower()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.organization_name} ({self.email})"
