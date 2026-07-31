import uuid

from django.conf import settings
from django.db import models


class Sensitivity(models.TextChoices):
    PUBLIC = "public", "Public"
    INTERNAL = "internal", "Internal"
    CONFIDENTIAL = "confidential", "Confidential"
    HIGHLY_SENSITIVE = "highly_sensitive", "Highly sensitive"
    RESTRICTED = "restricted", "Restricted"


class TenantRecord(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey(
        "identity.Organization",
        on_delete=models.CASCADE,
        related_name="%(class)s_records",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class Contact(TenantRecord):
    class ContactType(models.TextChoices):
        PERSON = "person", "Person"
        ORGANIZATION = "organization", "Organization"
        SERVICE_USER = "service_user", "Service user"
        DONOR = "donor", "Donor"
        VOLUNTEER = "volunteer", "Volunteer"

    class ConsentStatus(models.TextChoices):
        UNKNOWN = "unknown", "Unknown"
        GRANTED = "granted", "Granted"
        WITHDRAWN = "withdrawn", "Withdrawn"

    contact_type = models.CharField(
        max_length=24, choices=ContactType.choices, default=ContactType.PERSON
    )
    first_name = models.CharField(max_length=120, blank=True)
    last_name = models.CharField(max_length=120, blank=True)
    organization_name = models.CharField(max_length=200, blank=True)
    preferred_name = models.CharField(max_length=120, blank=True)
    email = models.EmailField(blank=True)
    phone = models.CharField(max_length=40, blank=True)
    external_ref = models.CharField(max_length=120, blank=True)
    sensitivity = models.CharField(
        max_length=24, choices=Sensitivity.choices, default=Sensitivity.INTERNAL
    )
    consent_status = models.CharField(
        max_length=16, choices=ConsentStatus.choices, default=ConsentStatus.UNKNOWN
    )
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ["last_name", "first_name", "organization_name"]
        indexes = [
            models.Index(fields=["organization", "email"]),
            models.Index(fields=["organization", "external_ref"]),
        ]

    @property
    def display_name(self):
        person_name = (
            f"{self.preferred_name or self.first_name} {self.last_name}".strip()
        )
        return person_name or self.organization_name or self.email or str(self.id)

    def __str__(self):
        return self.display_name


class Household(TenantRecord):
    name = models.CharField(max_length=200)
    primary_contact = models.ForeignKey(
        Contact, on_delete=models.SET_NULL, null=True, blank=True
    )
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ["name"]


class ContactRelationship(TenantRecord):
    from_contact = models.ForeignKey(
        Contact, on_delete=models.CASCADE, related_name="outgoing_relationships"
    )
    to_contact = models.ForeignKey(
        Contact, on_delete=models.CASCADE, related_name="incoming_relationships"
    )
    relation_type = models.CharField(max_length=80)
    notes = models.TextField(blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["organization", "from_contact", "to_contact", "relation_type"],
                name="unique_contact_relationship",
            )
        ]


class Interaction(TenantRecord):
    class Channel(models.TextChoices):
        EMAIL = "email", "Email"
        PHONE = "phone", "Phone"
        IN_PERSON = "in_person", "In person"
        SMS = "sms", "SMS"
        NOTE = "note", "Note"

    contact = models.ForeignKey(
        Contact, on_delete=models.CASCADE, related_name="interactions"
    )
    channel = models.CharField(
        max_length=16, choices=Channel.choices, default=Channel.NOTE
    )
    subject = models.CharField(max_length=240, blank=True)
    body = models.TextField()
    occurred_at = models.DateTimeField()
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True
    )

    class Meta:
        ordering = ["-occurred_at"]


class ConsentRecord(TenantRecord):
    contact = models.ForeignKey(
        Contact, on_delete=models.CASCADE, related_name="consent_records"
    )
    purpose = models.CharField(max_length=200)
    status = models.CharField(max_length=16, choices=Contact.ConsentStatus.choices)
    source = models.CharField(max_length=200, blank=True)
    recorded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True
    )
    expires_at = models.DateTimeField(null=True, blank=True)
    withdrawn_at = models.DateTimeField(null=True, blank=True)


class Program(TenantRecord):
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    active = models.BooleanField(default=True)
    sensitivity = models.CharField(
        max_length=24, choices=Sensitivity.choices, default=Sensitivity.INTERNAL
    )

    class Meta:
        ordering = ["name"]


class VolunteerProfile(TenantRecord):
    class Status(models.TextChoices):
        APPLICANT = "applicant", "Applicant"
        ACTIVE = "active", "Active"
        PAUSED = "paused", "Paused"
        INACTIVE = "inactive", "Inactive"

    contact = models.OneToOneField(
        Contact, on_delete=models.CASCADE, related_name="volunteer_profile"
    )
    status = models.CharField(
        max_length=16, choices=Status.choices, default=Status.APPLICANT
    )
    skills = models.JSONField(default=list)
    interests = models.JSONField(default=list)
    availability = models.JSONField(default=dict)
    emergency_contact_name = models.CharField(max_length=160, blank=True)
    emergency_contact_phone = models.CharField(max_length=40, blank=True)
    waiver_signed_at = models.DateTimeField(null=True, blank=True)
    notes = models.TextField(blank=True)


class VolunteerApplication(TenantRecord):
    class Status(models.TextChoices):
        RECEIVED = "received", "Received"
        REVIEWING = "reviewing", "Reviewing"
        ACCEPTED = "accepted", "Accepted"
        DECLINED = "declined", "Declined"
        WITHDRAWN = "withdrawn", "Withdrawn"

    applicant_name = models.CharField(max_length=200)
    email = models.EmailField()
    phone = models.CharField(max_length=40, blank=True)
    skills = models.JSONField(default=list)
    interests = models.JSONField(default=list)
    availability = models.JSONField(default=dict)
    status = models.CharField(
        max_length=16, choices=Status.choices, default=Status.RECEIVED
    )
    notes = models.TextField(blank=True)
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True
    )
    submitted_at = models.DateTimeField(auto_now_add=True)


class ScheduleEvent(TenantRecord):
    class EventType(models.TextChoices):
        APPOINTMENT = "appointment", "Appointment"
        SHIFT = "shift", "Volunteer shift"
        MEETING = "meeting", "Meeting"
        CLOSURE = "closure", "Closure"

    class Status(models.TextChoices):
        PLANNED = "planned", "Planned"
        CONFIRMED = "confirmed", "Confirmed"
        CANCELLED = "cancelled", "Cancelled"
        COMPLETED = "completed", "Completed"

    title = models.CharField(max_length=240)
    event_type = models.CharField(
        max_length=20, choices=EventType.choices, default=EventType.APPOINTMENT
    )
    status = models.CharField(
        max_length=16, choices=Status.choices, default=Status.PLANNED
    )
    starts_at = models.DateTimeField()
    ends_at = models.DateTimeField()
    recurrence_rule = models.CharField(max_length=240, blank=True)
    location = models.CharField(max_length=240, blank=True)
    notes = models.TextField(blank=True)
    program = models.ForeignKey(
        Program, on_delete=models.SET_NULL, null=True, blank=True
    )
    contact = models.ForeignKey(
        Contact, on_delete=models.SET_NULL, null=True, blank=True
    )
    volunteer = models.ForeignKey(
        VolunteerProfile, on_delete=models.SET_NULL, null=True, blank=True
    )
    reminder_sent = models.BooleanField(default=False)

    class Meta:
        ordering = ["starts_at"]
        indexes = [models.Index(fields=["organization", "starts_at"])]


class WaitlistEntry(TenantRecord):
    contact = models.ForeignKey(Contact, on_delete=models.CASCADE)
    program = models.ForeignKey(Program, on_delete=models.CASCADE)
    priority = models.PositiveIntegerField(default=100)
    requested_at = models.DateTimeField()
    status = models.CharField(
        max_length=16,
        choices=[
            ("waiting", "Waiting"),
            ("offered", "Offered"),
            ("fulfilled", "Fulfilled"),
            ("cancelled", "Cancelled"),
        ],
        default="waiting",
    )
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ["priority", "requested_at"]


class DocumentRecord(TenantRecord):
    class Status(models.TextChoices):
        UPLOADED = "uploaded", "Uploaded"
        PROCESSING = "processing", "Processing"
        READY = "ready", "Ready"
        FAILED = "failed", "Failed"
        DELETED = "deleted", "Deleted"

    title = models.CharField(max_length=240)
    file = models.FileField(upload_to="documents/%Y/%m")
    source_name = models.CharField(max_length=240, blank=True)
    mime_type = models.CharField(max_length=120, blank=True)
    size_bytes = models.PositiveBigIntegerField(default=0)
    checksum = models.CharField(max_length=128, blank=True)
    status = models.CharField(
        max_length=16, choices=Status.choices, default=Status.UPLOADED
    )
    sensitivity = models.CharField(
        max_length=24, choices=Sensitivity.choices, default=Sensitivity.INTERNAL
    )
    extracted_text = models.TextField(blank=True)
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True
    )
    deletion_requested = models.BooleanField(default=False)
    deleted_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]


class DocumentPassage(TenantRecord):
    document = models.ForeignKey(
        DocumentRecord, on_delete=models.CASCADE, related_name="passages"
    )
    text = models.TextField()
    page_number = models.PositiveIntegerField(null=True, blank=True)
    heading = models.CharField(max_length=240, blank=True)
    source_locator = models.CharField(max_length=240, blank=True)
    embedding = models.JSONField(default=list)


class Workflow(TenantRecord):
    class State(models.TextChoices):
        CREATED = "created", "Created"
        CLASSIFIED = "classified", "Classified"
        AWAITING_CONTEXT = "awaiting_context", "Awaiting context"
        RETRIEVING = "retrieving", "Retrieving"
        GENERATING = "generating", "Generating"
        VALIDATING = "validating", "Validating"
        AWAITING_REVIEW = "awaiting_review", "Awaiting review"
        APPROVED = "approved", "Approved"
        EXECUTING = "executing", "Executing"
        COMPLETED = "completed", "Completed"
        REJECTED = "rejected", "Rejected"
        FAILED = "failed", "Failed"
        CANCELLED = "cancelled", "Cancelled"

    workflow_type = models.CharField(max_length=80)
    state = models.CharField(
        max_length=24, choices=State.choices, default=State.CREATED
    )
    requested_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True
    )
    authorized_scope = models.JSONField(default=dict)
    inputs = models.JSONField(default=dict)
    sources = models.JSONField(default=list)
    prompt_version = models.CharField(max_length=80, blank=True)
    model_identifier = models.CharField(max_length=160, blank=True)
    runtime = models.CharField(max_length=80, blank=True)
    structured_output = models.JSONField(default=dict)
    validation_results = models.JSONField(default=dict)
    risk_flags = models.JSONField(default=list)
    approval_required = models.BooleanField(default=True)
    final_action = models.JSONField(default=dict)

    class Meta:
        ordering = ["-created_at"]


class WorkflowReview(TenantRecord):
    class Decision(models.TextChoices):
        PENDING = "pending", "Pending"
        APPROVED = "approved", "Approved"
        REJECTED = "rejected", "Rejected"

    workflow = models.ForeignKey(
        Workflow, on_delete=models.CASCADE, related_name="reviews"
    )
    reviewer = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True
    )
    decision = models.CharField(
        max_length=16, choices=Decision.choices, default=Decision.PENDING
    )
    comments = models.TextField(blank=True)
    decided_at = models.DateTimeField(null=True, blank=True)


class AIModelRegistry(TenantRecord):
    name = models.CharField(max_length=160)
    immutable_identifier = models.CharField(max_length=240)
    download_source = models.URLField(blank=True)
    checksum = models.CharField(max_length=128)
    license = models.CharField(max_length=120)
    intended_tasks = models.JSONField(default=list)
    prohibited_tasks = models.JSONField(default=list)
    quantization = models.CharField(max_length=80, blank=True)
    evaluation_date = models.DateField(null=True, blank=True)
    rollback_identifier = models.CharField(max_length=240, blank=True)
    enabled = models.BooleanField(default=False)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["organization", "immutable_identifier"],
                name="unique_model_identifier",
            )
        ]


class Mailbox(TenantRecord):
    name = models.CharField(max_length=160)
    address = models.EmailField()
    protocol = models.CharField(max_length=16, default="imap")
    host = models.CharField(max_length=240, blank=True)
    port = models.PositiveIntegerField(default=993)
    username = models.CharField(max_length=240, blank=True)
    credential_ref = models.CharField(max_length=240, blank=True)
    active = models.BooleanField(default=False)
    last_polled_at = models.DateTimeField(null=True, blank=True)


class EmailMessage(TenantRecord):
    mailbox = models.ForeignKey(
        Mailbox, on_delete=models.CASCADE, related_name="messages"
    )
    external_id = models.CharField(max_length=240)
    sender = models.EmailField()
    recipients = models.JSONField(default=list)
    subject = models.CharField(max_length=500)
    body_excerpt = models.TextField()
    received_at = models.DateTimeField()
    classification = models.CharField(max_length=80, blank=True)
    tasks = models.JSONField(default=list)
    deadline = models.DateTimeField(null=True, blank=True)
    injection_flags = models.JSONField(default=list)
    crm_contact = models.ForeignKey(
        Contact, on_delete=models.SET_NULL, null=True, blank=True
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["mailbox", "external_id"], name="unique_mailbox_message"
            )
        ]
        ordering = ["-received_at"]


class EmailDraft(TenantRecord):
    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        APPROVED = "approved", "Approved"
        REJECTED = "rejected", "Rejected"
        SENT = "sent", "Sent"

    message = models.ForeignKey(
        EmailMessage, on_delete=models.CASCADE, related_name="drafts"
    )
    subject = models.CharField(max_length=500)
    body = models.TextField()
    citations = models.JSONField(default=list)
    status = models.CharField(
        max_length=16, choices=Status.choices, default=Status.DRAFT
    )
    reviewer = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True
    )
    approved_at = models.DateTimeField(null=True, blank=True)
    sent_at = models.DateTimeField(null=True, blank=True)


class MetricDefinition(TenantRecord):
    key = models.SlugField(max_length=120)
    name = models.CharField(max_length=200)
    definition = models.TextField()
    unit = models.CharField(max_length=40, default="count")
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True
    )
    active = models.BooleanField(default=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["organization", "key"], name="unique_metric_key"
            )
        ]


class MetricSnapshot(TenantRecord):
    metric = models.ForeignKey(
        MetricDefinition, on_delete=models.CASCADE, related_name="snapshots"
    )
    period_start = models.DateField()
    period_end = models.DateField()
    value = models.DecimalField(max_digits=20, decimal_places=4)
    source_note = models.TextField(blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["metric", "period_start", "period_end"],
                name="unique_metric_period",
            )
        ]


class GrantWorkspace(TenantRecord):
    class Status(models.TextChoices):
        PLANNING = "planning", "Planning"
        IN_PROGRESS = "in_progress", "In progress"
        REVIEW = "review", "Review"
        SUBMITTED = "submitted", "Submitted"
        CLOSED = "closed", "Closed"

    name = models.CharField(max_length=240)
    funder = models.CharField(max_length=240)
    deadline = models.DateField(null=True, blank=True)
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.PLANNING
    )
    organizational_profile = models.TextField(blank=True)
    approved_statistics = models.JSONField(default=list)
    budget = models.JSONField(default=dict)


class GrantQuestion(TenantRecord):
    class Status(models.TextChoices):
        OPEN = "open", "Open"
        DRAFTED = "drafted", "Drafted"
        REVIEWED = "reviewed", "Reviewed"
        FINAL = "final", "Final"

    workspace = models.ForeignKey(
        GrantWorkspace, on_delete=models.CASCADE, related_name="questions"
    )
    question = models.TextField()
    answer_draft = models.TextField(blank=True)
    citations = models.JSONField(default=list)
    unsupported_claims = models.JSONField(default=list)
    status = models.CharField(
        max_length=16, choices=Status.choices, default=Status.OPEN
    )
    reviewer = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True
    )


class CommunityResource(TenantRecord):
    class Status(models.TextChoices):
        ACTIVE = "active", "Active"
        EXPIRED = "expired", "Expired"
        DRAFT = "draft", "Draft"
        ARCHIVED = "archived", "Archived"

    name = models.CharField(max_length=240)
    description = models.TextField()
    category = models.CharField(max_length=120)
    eligibility = models.TextField(blank=True)
    languages = models.JSONField(default=list)
    accessibility = models.JSONField(default=list)
    address = models.TextField(blank=True)
    latitude = models.DecimalField(
        max_digits=9, decimal_places=6, null=True, blank=True
    )
    longitude = models.DecimalField(
        max_digits=9, decimal_places=6, null=True, blank=True
    )
    hours = models.JSONField(default=dict)
    referral_method = models.CharField(max_length=240, blank=True)
    source_url = models.URLField(blank=True)
    source_organization = models.CharField(max_length=240, blank=True)
    last_verified_at = models.DateTimeField(null=True, blank=True)
    verification_interval_days = models.PositiveIntegerField(default=90)
    owner_name = models.CharField(max_length=160, blank=True)
    status = models.CharField(
        max_length=16, choices=Status.choices, default=Status.DRAFT
    )


class TranslationJob(TenantRecord):
    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        REVIEW = "review", "Review"
        APPROVED = "approved", "Approved"
        REJECTED = "rejected", "Rejected"

    source_language = models.CharField(max_length=16)
    target_language = models.CharField(max_length=16)
    source_text = models.TextField()
    translated_text = models.TextField(blank=True)
    glossary = models.JSONField(default=dict)
    model_version = models.CharField(max_length=160, blank=True)
    status = models.CharField(
        max_length=16, choices=Status.choices, default=Status.DRAFT
    )
    reviewer = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True
    )


class TranslationMemory(TenantRecord):
    source_language = models.CharField(max_length=16)
    target_language = models.CharField(max_length=16)
    source_text = models.TextField()
    translated_text = models.TextField()
    approved = models.BooleanField(default=False)
    model_version = models.CharField(max_length=160, blank=True)


class AccessibilityTransform(TenantRecord):
    class TransformType(models.TextChoices):
        PLAIN_LANGUAGE = "plain_language", "Plain language"
        IMAGE_DESCRIPTION = "image_description", "Image description"
        LARGE_PRINT = "large_print", "Large print"
        AUDIO = "audio", "Audio"
        OCR_CORRECTION = "ocr_correction", "OCR correction"

    source_type = models.CharField(max_length=80)
    source_id = models.CharField(max_length=120)
    transform_type = models.CharField(max_length=32, choices=TransformType.choices)
    original_text = models.TextField()
    transformed_text = models.TextField(blank=True)
    approved = models.BooleanField(default=False)
    reviewer = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True
    )


class VoiceCall(TenantRecord):
    class Status(models.TextChoices):
        RINGING = "ringing", "Ringing"
        ACTIVE = "active", "Active"
        TRANSFERRED = "transferred", "Transferred"
        CALLBACK = "callback", "Callback requested"
        COMPLETED = "completed", "Completed"
        ESCALATED = "escalated", "Escalated"

    external_id = models.CharField(max_length=240)
    caller_reference = models.CharField(max_length=160, blank=True)
    consent_captured = models.BooleanField(default=False)
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.RINGING
    )
    intent = models.CharField(max_length=80, blank=True)
    transcript = models.TextField(blank=True)
    recording_enabled = models.BooleanField(default=False)
    callback_requested = models.BooleanField(default=False)
    transfer_target = models.CharField(max_length=160, blank=True)
    started_at = models.DateTimeField()
    ended_at = models.DateTimeField(null=True, blank=True)
    safety_flags = models.JSONField(default=list)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["organization", "external_id"], name="unique_voice_call"
            )
        ]


class DonorSnapshot(TenantRecord):
    contact = models.ForeignKey(
        Contact, on_delete=models.CASCADE, related_name="donor_snapshots"
    )
    period_start = models.DateField()
    period_end = models.DateField()
    recency_days = models.PositiveIntegerField(null=True, blank=True)
    frequency = models.PositiveIntegerField(default=0)
    total_giving = models.DecimalField(max_digits=20, decimal_places=2, default=0)
    campaign_response = models.DecimalField(
        max_digits=8, decimal_places=4, null=True, blank=True
    )
    lapsed = models.BooleanField(default=False)
    communication_preference = models.CharField(max_length=80, blank=True)
    explanation = models.JSONField(default=list)
    opt_out = models.BooleanField(default=False)


class PluginPackage(TenantRecord):
    class Status(models.TextChoices):
        CATALOGUED = "catalogued", "Catalogued"
        APPROVED = "approved", "Approved"
        INSTALLED = "installed", "Installed"
        REVOKED = "revoked", "Revoked"

    name = models.CharField(max_length=200)
    version = models.CharField(max_length=80)
    publisher = models.CharField(max_length=200)
    manifest = models.JSONField(default=dict)
    permissions = models.JSONField(default=list)
    signature = models.TextField(blank=True)
    sbom = models.JSONField(default=dict)
    status = models.CharField(
        max_length=16, choices=Status.choices, default=Status.CATALOGUED
    )
    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True
    )
    approved_at = models.DateTimeField(null=True, blank=True)
    disabled_reason = models.TextField(blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["organization", "name", "version"], name="unique_plugin_release"
            )
        ]


class PluginInstallation(TenantRecord):
    package = models.ForeignKey(
        PluginPackage, on_delete=models.CASCADE, related_name="installations"
    )
    enabled = models.BooleanField(default=False)
    installed_at = models.DateTimeField(auto_now_add=True)
    config = models.JSONField(default=dict)


class PluginCapabilityToken(TenantRecord):
    installation = models.ForeignKey(
        PluginInstallation, on_delete=models.CASCADE, related_name="tokens"
    )
    token_hash = models.CharField(max_length=128)
    capabilities = models.JSONField(default=list)
    expires_at = models.DateTimeField(null=True, blank=True)
    revoked_at = models.DateTimeField(null=True, blank=True)


class PublicAPIClient(TenantRecord):
    name = models.CharField(max_length=160)
    client_id = models.CharField(max_length=120, unique=True)
    secret_hash = models.CharField(max_length=128)
    scopes = models.JSONField(default=list)
    active = models.BooleanField(default=True)
    rate_limit_per_minute = models.PositiveIntegerField(default=60)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True
    )


class RetentionPolicy(TenantRecord):
    record_type = models.CharField(max_length=120)
    retention_days = models.PositiveIntegerField()
    legal_hold = models.BooleanField(default=False)
    enabled = models.BooleanField(default=True)
    last_run_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["organization", "record_type"], name="unique_retention_policy"
            )
        ]
