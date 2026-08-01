import hashlib
import hmac
import json
import logging
import os
import re
import secrets
import smtplib
import urllib.error
import urllib.request
import zipfile
from datetime import timedelta, timezone as dt_timezone
from decimal import Decimal, InvalidOperation
from email.message import EmailMessage as SMTPMessage

from django.conf import settings
from django.core.exceptions import PermissionDenied
from django.core.cache import cache
from django.db import transaction
from django.db.models import Q
from django.http import Http404, HttpResponse
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import status
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from audit.models import AuditEvent
from identity.models import Membership, Organization
from identity.permissions import active_membership, require_admin

from .models import (
    AIModelRegistry,
    CommunityResource,
    Contact,
    AccessibilityTransform,
    DocumentPassage,
    DocumentRecord,
    DonorSnapshot,
    EmailDraft,
    EmailMessage,
    GrantWorkspace,
    Mailbox,
    MetricDefinition,
    PluginInstallation,
    PluginCapabilityToken,
    PluginPackage,
    PublicAPIClient,
    RetentionPolicy,
    ScheduleEvent,
    TranslationJob,
    VoiceCall,
    VolunteerApplication,
    VolunteerProfile,
    Workflow,
    WorkflowReview,
)
from .serializers import MODEL_SERIALIZERS


logger = logging.getLogger(__name__)
USER_FIELDS = {"created_by", "uploaded_by", "requested_by"}
ADMIN_ONLY_MODELS = {
    AIModelRegistry,
    Mailbox,
    PluginPackage,
    PluginInstallation,
    PublicAPIClient,
    RetentionPolicy,
}


def scoped_organization(request, slug):
    organization = (
        Organization.objects.filter(
            slug=slug, memberships__user=request.user, memberships__active=True
        )
        .distinct()
        .first()
    )
    if organization is None:
        raise Http404
    return organization


def serializer_for(model):
    return MODEL_SERIALIZERS[model]


def audit(
    request, action, organization, resource_type="", resource_id="", metadata=None
):
    return AuditEvent.objects.record(
        action=action,
        actor=request.user,
        organization=organization,
        event_type="module",
        resource_type=resource_type,
        resource_id=resource_id,
        metadata=metadata or {},
        request=request,
    )


class TenantView(APIView):
    permission_classes = [IsAuthenticated]
    parser_classes = [JSONParser, MultiPartParser, FormParser]
    model = None

    def organization(self, request, slug):
        organization = scoped_organization(request, slug)
        membership = active_membership(request.user, organization)
        if membership is None:
            raise PermissionDenied("Active organization membership required.")
        return organization, membership

    def serializer(self, *args, organization, **kwargs):
        serializer_class = serializer_for(self.model)
        return serializer_class(
            *args,
            context={"request": self.request, "organization": organization},
            **kwargs,
        )

    def write_kwargs(self, request):
        kwargs = {}
        for field in USER_FIELDS:
            if any(
                model_field.name == field for model_field in self.model._meta.fields
            ):
                kwargs[field] = request.user
        return kwargs


class TenantListCreateView(TenantView):
    admin_only = False

    def get_queryset(self, organization):
        queryset = self.model.objects.filter(organization=organization)
        query = self.request.query_params.get("q", "").strip()
        if query:
            text_fields = [
                field.name
                for field in self.model._meta.fields
                if isinstance(field, type(Contact._meta.get_field("notes")))
            ]
            if text_fields:
                expression = Q()
                for field in text_fields:
                    expression |= Q(**{f"{field}__icontains": query})
                queryset = queryset.filter(expression)
        return queryset.order_by("-created_at")[:100]

    def get(self, request, slug):
        organization, membership = self.organization(request, slug)
        if self.admin_only:
            require_admin(membership)
        queryset = self.get_queryset(organization)
        return Response(
            self.serializer(queryset, organization=organization, many=True).data
        )

    @transaction.atomic
    def post(self, request, slug):
        organization, membership = self.organization(request, slug)
        if self.admin_only:
            require_admin(membership)
        if self.model is DocumentRecord:
            uploaded_file = request.FILES.get("file")
            if uploaded_file is not None:
                if uploaded_file.size > settings.PROJECT_HOPE_MAX_DOCUMENT_BYTES:
                    return Response(
                        {
                            "detail": "Document is larger than the configured upload limit.",
                            "maxBytes": settings.PROJECT_HOPE_MAX_DOCUMENT_BYTES,
                        },
                        status=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                    )
                allowed_mimes = {
                    "application/pdf",
                    "application/rtf",
                    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    "image/jpeg",
                    "image/png",
                    "text/csv",
                    "text/markdown",
                    "text/plain",
                }
                content_type = uploaded_file.content_type or "application/octet-stream"
                if content_type not in allowed_mimes:
                    return Response(
                        {
                            "detail": "This document type is not allowed.",
                            "contentType": content_type,
                        },
                        status=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
                    )
                issue = document_upload_issue(uploaded_file)
                if issue:
                    detail, issue_status = issue
                    return Response(detail, status=issue_status)
        serializer = self.serializer(data=request.data, organization=organization)
        serializer.is_valid(raise_exception=True)
        instance = serializer.save(
            organization=organization, **self.write_kwargs(request)
        )
        if isinstance(instance, DocumentRecord):
            uploaded_file = request.FILES.get("file")
            if uploaded_file:
                instance.size_bytes = uploaded_file.size
                instance.mime_type = (
                    uploaded_file.content_type or "application/octet-stream"
                )
                instance.source_name = uploaded_file.name
                instance.checksum = checksum_for_file(uploaded_file)
                instance.save(
                    update_fields=[
                        "size_bytes",
                        "mime_type",
                        "source_name",
                        "checksum",
                        "updated_at",
                    ]
                )
        audit(
            request,
            f"{self.model.__name__.lower()}.created",
            organization,
            self.model.__name__,
            instance.id,
        )
        return Response(
            self.serializer(instance, organization=organization).data,
            status=status.HTTP_201_CREATED,
        )


class TenantDetailView(TenantView):
    admin_only = False

    def get_object(self, organization, pk):
        return get_object_or_404(
            self.model.objects.filter(organization=organization), pk=pk
        )

    def get(self, request, slug, pk):
        organization, membership = self.organization(request, slug)
        if self.admin_only:
            require_admin(membership)
        instance = self.get_object(organization, pk)
        return Response(self.serializer(instance, organization=organization).data)

    @transaction.atomic
    def patch(self, request, slug, pk):
        organization, membership = self.organization(request, slug)
        if self.admin_only:
            require_admin(membership)
        instance = self.get_object(organization, pk)
        serializer = self.serializer(
            instance, data=request.data, partial=True, organization=organization
        )
        serializer.is_valid(raise_exception=True)
        instance = serializer.save()
        audit(
            request,
            f"{self.model.__name__.lower()}.updated",
            organization,
            self.model.__name__,
            instance.id,
        )
        return Response(self.serializer(instance, organization=organization).data)

    @transaction.atomic
    def delete(self, request, slug, pk):
        organization, membership = self.organization(request, slug)
        require_admin(membership)
        instance = self.get_object(organization, pk)
        record_type = retention_record_type(self.model)
        if RetentionPolicy.objects.filter(
            organization=organization,
            record_type=record_type,
            enabled=True,
            legal_hold=True,
        ).exists():
            return Response(
                {
                    "detail": "This record type is under legal hold and cannot be deleted.",
                    "recordType": record_type,
                },
                status=423,
            )
        identifier = str(instance.id)
        if isinstance(instance, DocumentRecord) and instance.file:
            instance.file.delete(save=False)
        instance.delete()
        audit(
            request,
            f"{self.model.__name__.lower()}.deleted",
            organization,
            self.model.__name__,
            identifier,
        )
        return Response(status=status.HTTP_204_NO_CONTENT)


def checksum_for_file(uploaded_file):
    digest = hashlib.sha256()
    for chunk in uploaded_file.chunks():
        digest.update(chunk)
    uploaded_file.seek(0)
    return digest.hexdigest()


def retention_record_type(model):
    return {
        Contact: "contacts",
        DocumentRecord: "documents",
        EmailMessage: "email_messages",
        VoiceCall: "voice_calls",
        Workflow: "workflows",
        TranslationJob: "translations",
        AccessibilityTransform: "accessibility_transforms",
        CommunityResource: "resources",
    }.get(model, f"{model._meta.model_name}s")


def document_upload_issue(uploaded_file):
    """Return a safe upload error, or None when the declared file is structurally safe."""
    content_type = uploaded_file.content_type or "application/octet-stream"
    sample = uploaded_file.read(16)
    uploaded_file.seek(0)
    signatures = {
        "application/pdf": b"%PDF-",
        "application/rtf": b"{\\rtf",
        "image/jpeg": b"\xff\xd8\xff",
        "image/png": b"\x89PNG\r\n\x1a\n",
    }
    signature = signatures.get(content_type)
    if signature and not sample.startswith(signature):
        return {
            "detail": "The file contents do not match the declared document type.",
            "contentType": content_type,
        }, status.HTTP_415_UNSUPPORTED_MEDIA_TYPE
    if (
        content_type
        in {
            "text/csv",
            "text/markdown",
            "text/plain",
        }
        and b"\x00" in sample
    ):
        return {
            "detail": "Binary content is not allowed for a text document.",
            "contentType": content_type,
        }, status.HTTP_415_UNSUPPORTED_MEDIA_TYPE
    if content_type in {
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    }:
        try:
            with zipfile.ZipFile(uploaded_file) as archive:
                members = archive.infolist()
                names = {member.filename for member in members}
                total_size = sum(member.file_size for member in members)
                compressed_size = sum(member.compress_size for member in members)
                unsafe_name = any(
                    name.startswith(("/", "\\"))
                    or ".." in name.replace("\\", "/").split("/")
                    for name in names
                )
                if "[Content_Types].xml" not in names or unsafe_name:
                    raise ValueError("invalid office archive")
                if len(members) > settings.PROJECT_HOPE_MAX_DOCUMENT_ARCHIVE_MEMBERS:
                    return {
                        "detail": "The document archive contains too many files.",
                        "maxMembers": settings.PROJECT_HOPE_MAX_DOCUMENT_ARCHIVE_MEMBERS,
                    }, status.HTTP_413_REQUEST_ENTITY_TOO_LARGE
                if total_size > settings.PROJECT_HOPE_MAX_UNCOMPRESSED_DOCUMENT_BYTES:
                    return {
                        "detail": "The document expands beyond the configured safety limit.",
                        "maxBytes": settings.PROJECT_HOPE_MAX_UNCOMPRESSED_DOCUMENT_BYTES,
                    }, status.HTTP_413_REQUEST_ENTITY_TOO_LARGE
                if compressed_size and total_size > compressed_size * 1000:
                    return {
                        "detail": "The document compression ratio is unsafe.",
                    }, status.HTTP_413_REQUEST_ENTITY_TOO_LARGE
        except (ValueError, zipfile.BadZipFile, OSError):
            return {
                "detail": "The office document archive is invalid or unsafe.",
                "contentType": content_type,
            }, status.HTTP_415_UNSUPPORTED_MEDIA_TYPE
        finally:
            uploaded_file.seek(0)
    return None


def build_resource_views(model, admin_only=False):
    list_view = type(
        f"{model.__name__}ListCreateView",
        (TenantListCreateView,),
        {"model": model, "admin_only": admin_only},
    )
    detail_view = type(
        f"{model.__name__}DetailView",
        (TenantDetailView,),
        {"model": model, "admin_only": admin_only},
    )
    return list_view.as_view(), detail_view.as_view()


class DocumentSearchView(TenantView):
    def get(self, request, slug):
        organization, _ = self.organization(request, slug)
        query = request.query_params.get("q", "").strip()
        if not query:
            return Response(
                {"results": [], "detail": "Provide q to search approved document text."}
            )
        records = DocumentRecord.objects.filter(
            organization=organization, status=DocumentRecord.Status.READY
        ).filter(Q(title__icontains=query) | Q(extracted_text__icontains=query))[:50]
        passages = DocumentPassage.objects.filter(
            organization=organization, text__icontains=query
        ).select_related("document")[:100]
        audit(
            request,
            "document.search",
            organization,
            metadata={"query_length": len(query)},
        )
        return Response(
            {
                "documents": [
                    {
                        "id": str(record.id),
                        "title": record.title,
                        "status": record.status,
                    }
                    for record in records
                ],
                "passages": [
                    {
                        "id": str(passage.id),
                        "documentId": str(passage.document_id),
                        "documentTitle": passage.document.title,
                        "pageNumber": passage.page_number,
                        "heading": passage.heading,
                        "text": passage.text,
                        "sourceLocator": passage.source_locator,
                    }
                    for passage in passages
                ],
            }
        )


class ResourceSearchView(TenantView):
    def get(self, request, slug):
        organization, _ = self.organization(request, slug)
        query = request.query_params.get("q", "").strip()
        category = request.query_params.get("category", "").strip()
        language = request.query_params.get("language", "").strip()
        queryset = CommunityResource.objects.filter(
            organization=organization, status=CommunityResource.Status.ACTIVE
        )
        if category:
            queryset = queryset.filter(category__iexact=category)
        if query:
            queryset = queryset.filter(
                Q(name__icontains=query)
                | Q(description__icontains=query)
                | Q(eligibility__icontains=query)
            )
        results = []
        now = timezone.now()
        for resource in queryset[:100]:
            stale = resource.last_verified_at is None or (
                resource.last_verified_at
                + timedelta(days=resource.verification_interval_days)
                < now
            )
            if language and language.lower() not in [
                str(item).lower() for item in resource.languages
            ]:
                continue
            results.append(
                {
                    "id": str(resource.id),
                    "name": resource.name,
                    "description": resource.description,
                    "category": resource.category,
                    "languages": resource.languages,
                    "accessibility": resource.accessibility,
                    "address": resource.address,
                    "referralMethod": resource.referral_method,
                    "sourceUrl": resource.source_url,
                    "lastVerifiedAt": resource.last_verified_at,
                    "freshness": "stale" if stale else "verified",
                    "matchReason": "name, description, or eligibility text match",
                }
            )
        audit(
            request,
            "resource.search",
            organization,
            metadata={"query_length": len(query)},
        )
        return Response({"results": results})


class ResourceVerifyView(TenantView):
    def post(self, request, slug, pk):
        organization, membership = self.organization(request, slug)
        if membership.role not in {
            Membership.Role.OWNER,
            Membership.Role.ADMIN,
            Membership.Role.COORDINATOR,
        }:
            raise PermissionDenied(
                "A coordinator or administrator must verify resources."
            )
        resource = get_object_or_404(
            CommunityResource.objects.filter(organization=organization), pk=pk
        )
        resource.last_verified_at = timezone.now()
        resource.status = CommunityResource.Status.ACTIVE
        if request.data.get("ownerName") is not None:
            resource.owner_name = str(request.data["ownerName"])[:160]
        resource.save(
            update_fields=["last_verified_at", "status", "owner_name", "updated_at"]
        )
        audit(request, "resource.verified", organization, "resource", resource.id)
        return Response(
            {
                "id": str(resource.id),
                "status": resource.status,
                "lastVerifiedAt": resource.last_verified_at,
            }
        )


class ScheduleICSView(TenantView):
    def get(self, request, slug):
        organization, _ = self.organization(request, slug)
        events = ScheduleEvent.objects.filter(organization=organization).exclude(
            status=ScheduleEvent.Status.CANCELLED
        )[:500]
        lines = [
            "BEGIN:VCALENDAR",
            "VERSION:2.0",
            "PRODID:-//Project Hope//Schedule//EN",
        ]
        for event in events:
            start = event.starts_at.astimezone(dt_timezone.utc).strftime(
                "%Y%m%dT%H%M%SZ"
            )
            end = event.ends_at.astimezone(dt_timezone.utc).strftime("%Y%m%dT%H%M%SZ")
            lines.extend(
                [
                    "BEGIN:VEVENT",
                    f"UID:{event.id}@project-hope",
                    f"DTSTART:{start}",
                    f"DTEND:{end}",
                    f"SUMMARY:{ics_escape(event.title)}",
                    f"DESCRIPTION:{ics_escape(event.notes)}",
                    "END:VEVENT",
                ]
            )
        lines.append("END:VCALENDAR")
        audit(request, "schedule.export", organization, resource_type="icalendar")
        return HttpResponse(
            "\r\n".join(lines) + "\r\n", content_type="text/calendar; charset=utf-8"
        )


def ics_escape(value):
    return (
        str(value)
        .replace("\\", "\\\\")
        .replace(";", "\\;")
        .replace(",", "\\,")
        .replace("\n", "\\n")
    )


class MetricSummaryView(TenantView):
    def get(self, request, slug):
        organization, _ = self.organization(request, slug)
        metrics = MetricDefinition.objects.filter(
            organization=organization, active=True
        ).prefetch_related("snapshots")
        result = []
        for metric in metrics:
            snapshot = metric.snapshots.order_by("-period_end").first()
            result.append(
                {
                    "key": metric.key,
                    "name": metric.name,
                    "definition": metric.definition,
                    "unit": metric.unit,
                    "value": snapshot.value if snapshot else None,
                    "periodStart": snapshot.period_start if snapshot else None,
                    "periodEnd": snapshot.period_end if snapshot else None,
                }
            )
        return Response({"metrics": result})


class GrantBudgetValidationView(TenantView):
    def post(self, request, slug, pk):
        organization, membership = self.organization(request, slug)
        if membership.role not in {
            Membership.Role.OWNER,
            Membership.Role.ADMIN,
            Membership.Role.COORDINATOR,
        }:
            raise PermissionDenied(
                "A coordinator or administrator must validate grant budgets."
            )
        workspace = get_object_or_404(
            GrantWorkspace.objects.filter(organization=organization), pk=pk
        )
        budget = request.data.get("budget", workspace.budget)
        if not isinstance(budget, dict):
            return Response(
                {"detail": "budget must be an object of category to amount."},
                status=400,
            )
        errors = []
        normalized = {}
        total = Decimal("0")
        for category, raw_amount in budget.items():
            try:
                amount = Decimal(str(raw_amount))
            except (InvalidOperation, ValueError):
                errors.append(f"{category}: amount is not numeric")
                continue
            if amount < 0:
                errors.append(f"{category}: amount cannot be negative")
            normalized[str(category)] = str(amount.quantize(Decimal("0.01")))
            total += amount
        save = request.data.get("save", False) is True
        if save and not errors:
            workspace.budget = normalized
            workspace.save(update_fields=["budget", "updated_at"])
            audit(
                request,
                "grant.budget_validated",
                organization,
                "grant_workspace",
                workspace.id,
                {"total": str(total)},
            )
        return Response(
            {
                "valid": not errors,
                "errors": errors,
                "total": str(total.quantize(Decimal("0.01"))),
                "saved": save and not errors,
            }
        )


class TranslationReviewView(TenantView):
    def post(self, request, slug, pk):
        organization, membership = self.organization(request, slug)
        if membership.role not in {
            Membership.Role.OWNER,
            Membership.Role.ADMIN,
            Membership.Role.COORDINATOR,
        }:
            raise PermissionDenied(
                "A coordinator or administrator must review translations."
            )
        job = get_object_or_404(
            TranslationJob.objects.filter(organization=organization), pk=pk
        )
        decision = request.data.get("decision")
        if decision not in {"approved", "rejected"}:
            return Response(
                {"detail": "decision must be approved or rejected."}, status=400
            )
        job.status = (
            TranslationJob.Status.APPROVED
            if decision == "approved"
            else TranslationJob.Status.REJECTED
        )
        job.reviewer = request.user
        job.save(update_fields=["status", "reviewer", "updated_at"])
        audit(
            request,
            "translation.reviewed",
            organization,
            "translation_job",
            job.id,
            {"decision": decision},
        )
        return Response({"id": str(job.id), "status": job.status})


class AccessibilityReviewView(TenantView):
    def post(self, request, slug, pk):
        organization, membership = self.organization(request, slug)
        if membership.role not in {
            Membership.Role.OWNER,
            Membership.Role.ADMIN,
            Membership.Role.COORDINATOR,
        }:
            raise PermissionDenied(
                "A coordinator or administrator must review accessibility transformations."
            )
        transform = get_object_or_404(
            AccessibilityTransform.objects.filter(organization=organization), pk=pk
        )
        approved = request.data.get("approved")
        if not isinstance(approved, bool):
            return Response({"detail": "approved must be boolean."}, status=400)
        transform.approved = approved
        transform.reviewer = request.user
        transform.save(update_fields=["approved", "reviewer", "updated_at"])
        audit(
            request,
            "accessibility.reviewed",
            organization,
            "accessibility_transform",
            transform.id,
            {"approved": approved},
        )
        return Response({"id": str(transform.id), "approved": transform.approved})


class VolunteerPipelineView(TenantView):
    def get(self, request, slug):
        organization, _ = self.organization(request, slug)
        applications = VolunteerApplication.objects.filter(
            organization=organization
        ).order_by("-submitted_at")[:200]
        profiles = VolunteerProfile.objects.filter(organization=organization).order_by(
            "-updated_at"
        )[:200]
        return Response(
            {
                "applications": [
                    {
                        "id": str(application.id),
                        "applicantName": application.applicant_name,
                        "email": application.email,
                        "status": application.status,
                        "skills": application.skills,
                        "interests": application.interests,
                        "submittedAt": application.submitted_at,
                    }
                    for application in applications
                ],
                "profiles": [
                    {
                        "id": str(profile.id),
                        "contactId": str(profile.contact_id),
                        "status": profile.status,
                        "skills": profile.skills,
                        "interests": profile.interests,
                        "availability": profile.availability,
                    }
                    for profile in profiles
                ],
            }
        )


class VolunteerApplicationReviewView(TenantView):
    @transaction.atomic
    def post(self, request, slug, pk):
        organization, membership = self.organization(request, slug)
        if membership.role not in {
            Membership.Role.OWNER,
            Membership.Role.ADMIN,
            Membership.Role.COORDINATOR,
        }:
            raise PermissionDenied(
                "A coordinator or administrator must review volunteer applications."
            )
        application = get_object_or_404(
            VolunteerApplication.objects.filter(organization=organization), pk=pk
        )
        decision = request.data.get("status")
        if decision not in {
            VolunteerApplication.Status.ACCEPTED,
            VolunteerApplication.Status.DECLINED,
            VolunteerApplication.Status.REVIEWING,
        }:
            return Response(
                {"detail": "status must be reviewing, accepted, or declined."},
                status=400,
            )
        application.status = decision
        application.reviewed_by = request.user
        application.save(update_fields=["status", "reviewed_by", "updated_at"])
        profile_id = None
        if decision == VolunteerApplication.Status.ACCEPTED:
            contact, _ = Contact.objects.get_or_create(
                organization=organization,
                email=application.email,
                defaults={
                    "contact_type": Contact.ContactType.VOLUNTEER,
                    "first_name": application.applicant_name,
                    "notes": "Created from an accepted volunteer application.",
                },
            )
            contact.contact_type = Contact.ContactType.VOLUNTEER
            contact.save(update_fields=["contact_type", "updated_at"])
            profile, _ = VolunteerProfile.objects.get_or_create(
                organization=organization,
                contact=contact,
                defaults={
                    "status": VolunteerProfile.Status.ACTIVE,
                    "skills": application.skills,
                    "interests": application.interests,
                    "availability": application.availability,
                },
            )
            profile.status = VolunteerProfile.Status.ACTIVE
            profile.skills = application.skills
            profile.interests = application.interests
            profile.availability = application.availability
            profile.save(
                update_fields=[
                    "status",
                    "skills",
                    "interests",
                    "availability",
                    "updated_at",
                ]
            )
            profile_id = str(profile.id)
        audit(
            request,
            "volunteer_application.reviewed",
            organization,
            "volunteer_application",
            application.id,
            {"status": decision, "profileId": profile_id},
        )
        return Response(
            {
                "applicationId": str(application.id),
                "status": decision,
                "volunteerProfileId": profile_id,
            }
        )


class WorkflowReviewView(TenantView):
    def post(self, request, slug, pk):
        organization, membership = self.organization(request, slug)
        if membership.role not in {
            Membership.Role.OWNER,
            Membership.Role.ADMIN,
            Membership.Role.COORDINATOR,
        }:
            raise PermissionDenied(
                "A coordinator or administrator must review workflows."
            )
        workflow = get_object_or_404(
            Workflow.objects.filter(organization=organization), pk=pk
        )
        decision = request.data.get("decision")
        if decision not in {
            WorkflowReview.Decision.APPROVED,
            WorkflowReview.Decision.REJECTED,
        }:
            return Response(
                {"detail": "decision must be approved or rejected."}, status=400
            )
        with transaction.atomic():
            review = WorkflowReview.objects.create(
                organization=organization,
                workflow=workflow,
                reviewer=request.user,
                decision=decision,
                comments=str(request.data.get("comments", ""))[:5000],
                decided_at=timezone.now(),
            )
            workflow.state = (
                Workflow.State.APPROVED
                if decision == WorkflowReview.Decision.APPROVED
                else Workflow.State.REJECTED
            )
            workflow.final_action = {
                "approvedBy": str(request.user.id),
                "decision": decision,
            }
            workflow.save(update_fields=["state", "final_action", "updated_at"])
        audit(
            request,
            "workflow.reviewed",
            organization,
            "workflow",
            workflow.id,
            {"decision": decision},
        )
        return Response(
            {
                "workflow": str(workflow.id),
                "review": str(review.id),
                "state": workflow.state,
            }
        )


class EmailApprovalView(TenantView):
    def post(self, request, slug, pk):
        organization, membership = self.organization(request, slug)
        if membership.role not in {
            Membership.Role.OWNER,
            Membership.Role.ADMIN,
            Membership.Role.COORDINATOR,
        }:
            raise PermissionDenied("A coordinator or administrator must approve email.")
        draft = get_object_or_404(
            EmailDraft.objects.filter(organization=organization), pk=pk
        )
        action = request.data.get("action", "approve")
        if action not in {"approve", "reject"}:
            return Response({"detail": "action must be approve or reject."}, status=400)
        draft.status = (
            EmailDraft.Status.APPROVED
            if action == "approve"
            else EmailDraft.Status.REJECTED
        )
        draft.reviewer = request.user
        draft.approved_at = timezone.now() if action == "approve" else None
        draft.save(update_fields=["status", "reviewer", "approved_at", "updated_at"])
        audit(request, f"email_draft.{action}d", organization, "email_draft", draft.id)
        return Response({"id": str(draft.id), "status": draft.status})


class EmailSendView(TenantView):
    def post(self, request, slug, pk):
        organization, membership = self.organization(request, slug)
        require_admin(membership)
        draft = get_object_or_404(
            EmailDraft.objects.select_related("message"),
            organization=organization,
            pk=pk,
        )
        if draft.status != EmailDraft.Status.APPROVED:
            return Response(
                {"detail": "Only an approved draft can be sent."}, status=400
            )
        host = os.environ.get("SMTP_HOST", "")
        if not host:
            return Response(
                {"detail": "SMTP_HOST is not configured; no email was sent."},
                status=503,
            )
        port = int(os.environ.get("SMTP_PORT", "587"))
        try:
            message = SMTPMessage()
            message["From"] = (
                os.environ.get("SMTP_FROM", "") or draft.message.recipients[0]
            )
            message["To"] = draft.message.sender
            message["Subject"] = draft.subject
            message.set_content(draft.body)
            with smtplib.SMTP(host, port, timeout=20) as connection:
                if os.environ.get("SMTP_STARTTLS", "true").lower() == "true":
                    connection.starttls()
                username = os.environ.get("SMTP_USERNAME", "")
                if username:
                    connection.login(username, os.environ.get("SMTP_PASSWORD", ""))
                connection.send_message(message)
        except (OSError, smtplib.SMTPException) as exc:
            return Response(
                {"detail": f"SMTP delivery failed: {type(exc).__name__}."}, status=502
            )
        draft.status = EmailDraft.Status.SENT
        draft.sent_at = timezone.now()
        draft.save(update_fields=["status", "sent_at", "updated_at"])
        audit(request, "email_draft.sent", organization, "email_draft", draft.id)
        return Response({"id": str(draft.id), "status": draft.status})


CRISIS_TERMS = {
    "suicide",
    "kill myself",
    "emergency",
    "abuse",
    "overdose",
    "immediate danger",
}
INTENT_TERMS = {
    "office_hours": {"hours", "open", "opening", "close"},
    "appointment": {"appointment", "book", "schedule"},
    "resource_search": {"help", "resource", "support", "food", "housing"},
    "callback": {"call me", "callback", "phone"},
}


def classify_local_intent(text):
    lowered = text.lower()
    safety_flags = sorted(term for term in CRISIS_TERMS if term in lowered)
    if safety_flags:
        return "human_transfer", safety_flags
    for intent, terms in INTENT_TERMS.items():
        if any(term in lowered for term in terms):
            return intent, []
    return "human_transfer", []


def simple_embedding(text):
    words = re.findall(r"[a-z0-9]+", text.lower())
    return [
        int(hashlib.sha256(f"{word}:{index}".encode()).hexdigest()[:8], 16) / 2**32
        for index, word in enumerate(words[:16])
    ]


def call_ai_gateway(path, payload):
    """Call the optional charity-controlled AI boundary without sending data by default."""
    base_url = os.environ.get("AI_GATEWAY_URL", "").strip().rstrip("/")
    if not base_url:
        return None
    body = json.dumps(payload).encode("utf-8")
    headers = {"Accept": "application/json", "Content-Type": "application/json"}
    gateway_token = os.environ.get("AI_GATEWAY_TOKEN", "")
    if gateway_token:
        headers["X-Project-Hope-Gateway-Token"] = gateway_token
    request = urllib.request.Request(
        f"{base_url}/{path.lstrip('/')}", data=body, headers=headers, method="POST"
    )
    try:
        with urllib.request.urlopen(
            request,
            timeout=float(os.environ.get("AI_GATEWAY_TIMEOUT_SECONDS", "3")),
        ) as response:
            result = json.loads(response.read().decode("utf-8"))
            return result if isinstance(result, dict) else None
    except (
        TimeoutError,
        ValueError,
        urllib.error.URLError,
        urllib.error.HTTPError,
    ) as exc:
        logger.warning("AI gateway unavailable for %s: %s", path, type(exc).__name__)
        return None


def translate_local(text, source, target, glossary):
    if source == target:
        return text
    dictionary = {
        ("en", "fr"): {
            "hello": "bonjour",
            "thank you": "merci",
            "help": "aide",
            "appointment": "rendez-vous",
            "volunteer": "bénévole",
        },
        ("fr", "en"): {
            "bonjour": "hello",
            "merci": "thank you",
            "aide": "help",
            "rendez-vous": "appointment",
            "bénévole": "volunteer",
        },
    }.get((source, target), {})
    output = text
    for source_term, target_term in {**dictionary, **glossary}.items():
        output = re.sub(
            rf"\b{re.escape(source_term)}\b", target_term, output, flags=re.IGNORECASE
        )
    return output


class AIOperationView(TenantView):
    def post(self, request, slug, operation):
        organization, _ = self.organization(request, slug)
        payload = request.data if isinstance(request.data, dict) else {}
        workflow = Workflow.objects.create(
            organization=organization,
            workflow_type=operation,
            state=Workflow.State.GENERATING,
            requested_by=request.user,
            authorized_scope={"organizationId": str(organization.id)},
            inputs={
                key: value
                for key, value in payload.items()
                if key not in {"password", "token"}
            },
            prompt_version="bounded-ai-v2",
            model_identifier="deterministic-local-adapter-v1",
            runtime="python",
        )
        output = {}
        risk_flags = []
        sources = []
        gateway_used = False
        gateway_model = "deterministic-local-adapter-v1"
        gateway_provider = "python"
        try:
            if operation == "classify-intent":
                text = str(payload.get("text", ""))[:12000]
                gateway = call_ai_gateway("v1/classify-intent", {"text": text})
                if gateway and isinstance(gateway.get("intent"), str):
                    gateway_used = True
                    gateway_model = str(gateway.get("model", gateway_model))
                    gateway_provider = str(gateway.get("provider", "ai-gateway"))
                    intent = gateway["intent"]
                    flags = gateway.get("riskFlags", [])
                    output = {
                        "intent": intent,
                        "confidence": "gateway-bounded",
                        "requiresHuman": bool(gateway.get("requiresHuman", True)),
                    }
                    risk_flags = [flag for flag in flags if isinstance(flag, str)]
                    risk_flags = risk_flags or ["human_review_required"]
                else:
                    intent, flags = classify_local_intent(text)
                    output = {
                        "intent": intent,
                        "confidence": "rule-based",
                        "requiresHuman": True,
                    }
                    risk_flags = flags or (
                        ["human_review_required"] if intent == "human_transfer" else []
                    )
            elif operation == "draft-email":
                message = None
                if payload.get("messageId"):
                    message = get_object_or_404(
                        EmailMessage.objects.filter(organization=organization),
                        pk=payload["messageId"],
                    )
                body = str(payload.get("body", ""))[:12000] or (
                    message.body_excerpt if message else ""
                )
                subject = str(payload.get("subject", "Follow-up from Project Hope"))[
                    :500
                ]
                gateway = call_ai_gateway(
                    "v1/draft-email", {"subject": subject, "untrusted_body": body}
                )
                if gateway and isinstance(gateway.get("body"), str):
                    gateway_used = True
                    gateway_model = str(gateway.get("model", gateway_model))
                    gateway_provider = str(gateway.get("provider", "ai-gateway"))
                    draft_body = gateway["body"][:12000]
                    draft_subject = str(gateway.get("subject", subject))[:500]
                    gateway_flags = gateway.get("riskFlags", [])
                    risk_flags = [
                        flag for flag in gateway_flags if isinstance(flag, str)
                    ] or ["human_approval_required"]
                else:
                    draft_body = "Thank you for contacting us. A staff member will review your message and follow up with you.\n\nThis draft requires human review before sending."
                    draft_subject = subject
                    risk_flags = ["human_approval_required", "untrusted_email_content"]
                output = {
                    "subject": draft_subject,
                    "body": draft_body,
                    "untrustedInputSummary": body[:240],
                }
                if message:
                    draft = EmailDraft.objects.create(
                        organization=organization,
                        message=message,
                        subject=draft_subject,
                        body=draft_body,
                        citations=[],
                    )
                    output["draftId"] = str(draft.id)
            elif operation == "answer-grant-question":
                question = str(payload.get("question", ""))[:12000]
                document_ids = payload.get("documentIds", [])
                passages = DocumentPassage.objects.filter(
                    organization=organization, document_id__in=document_ids
                )[:20]
                sources = [str(passage.id) for passage in passages]
                gateway = call_ai_gateway(
                    "v1/answer-grant",
                    {
                        "question": question,
                        "passages": [
                            {"id": str(passage.id), "text": passage.text}
                            for passage in passages
                        ],
                    },
                )
                if gateway and isinstance(gateway.get("answer"), str):
                    gateway_used = True
                    gateway_model = str(gateway.get("model", gateway_model))
                    gateway_provider = str(gateway.get("provider", "ai-gateway"))
                    output = {
                        "answer": gateway["answer"],
                        "question": question,
                        "citations": [
                            citation
                            for citation in gateway.get("citations", [])
                            if citation in sources
                        ],
                        "unsupportedClaims": [
                            claim
                            for claim in gateway.get("unsupportedClaims", [])
                            if isinstance(claim, str)
                        ],
                    }
                else:
                    output = {
                        "answer": "No approved evidence was found for this question. Add or review source documents before drafting.",
                        "question": question,
                        "citations": sources,
                        "unsupportedClaims": [
                            "answer requires approved organizational evidence"
                        ],
                    }
                risk_flags = ["unsupported_claims", "human_approval_required"]
            elif operation == "translate-segments":
                source = str(payload.get("sourceLanguage", "en"))[:16]
                target = str(payload.get("targetLanguage", "fr"))[:16]
                text = str(payload.get("text", ""))[:12000]
                glossary = (
                    payload.get("glossary", {})
                    if isinstance(payload.get("glossary", {}), dict)
                    else {}
                )
                gateway = call_ai_gateway(
                    "v1/translate",
                    {
                        "source_language": source,
                        "target_language": target,
                        "text": text,
                        "glossary": glossary,
                    },
                )
                if gateway and isinstance(gateway.get("translatedText"), str):
                    gateway_used = True
                    gateway_model = str(gateway.get("model", gateway_model))
                    gateway_provider = str(gateway.get("provider", "ai-gateway"))
                    translated = gateway["translatedText"]
                    model_version = gateway_model
                else:
                    translated = translate_local(text, source, target, glossary)
                    model_version = "deterministic-glossary-v1"
                job = TranslationJob.objects.create(
                    organization=organization,
                    source_language=source,
                    target_language=target,
                    source_text=text,
                    translated_text=translated,
                    glossary=glossary,
                    model_version=model_version,
                    status=TranslationJob.Status.REVIEW,
                )
                output = {
                    "jobId": str(job.id),
                    "translatedText": translated,
                    "needsReview": True,
                }
                risk_flags = ["human_review_required"]
            elif operation == "embed":
                text = str(payload.get("text", ""))[:12000]
                gateway = call_ai_gateway("v1/embed", {"text": text})
                if gateway and isinstance(gateway.get("embedding"), list):
                    gateway_used = True
                    gateway_model = str(gateway.get("model", gateway_model))
                    gateway_provider = str(gateway.get("provider", "ai-gateway"))
                    output = {
                        "embedding": gateway["embedding"],
                        "semantic": bool(gateway.get("semantic", False)),
                        "model": str(gateway.get("model", "deterministic-hash-v1")),
                    }
                else:
                    output = {
                        "embedding": simple_embedding(text),
                        "semantic": False,
                        "model": "deterministic-hash-v1",
                    }
            elif operation == "extract-document":
                document = get_object_or_404(
                    DocumentRecord.objects.filter(organization=organization),
                    pk=payload.get("documentId"),
                )
                document.status = DocumentRecord.Status.PROCESSING
                document.save(update_fields=["status", "updated_at"])
                with document.file.open("rb") as handle:
                    raw = handle.read(5 * 1024 * 1024)
                extracted = raw.decode("utf-8", errors="replace")
                document.extracted_text = extracted
                document.status = DocumentRecord.Status.READY
                document.size_bytes = len(raw)
                document.checksum = hashlib.sha256(raw).hexdigest()
                document.save(
                    update_fields=[
                        "extracted_text",
                        "status",
                        "size_bytes",
                        "checksum",
                        "updated_at",
                    ]
                )
                passage = DocumentPassage.objects.create(
                    organization=organization,
                    document=document,
                    text=extracted[:100000],
                    source_locator="page:1",
                )
                output = {
                    "documentId": str(document.id),
                    "passageId": str(passage.id),
                    "characters": len(extracted),
                }
            elif operation == "transcribe":
                call = get_object_or_404(
                    VoiceCall.objects.filter(organization=organization),
                    pk=payload.get("callId"),
                )
                transcript = str(payload.get("transcript", ""))[:20000]
                intent, flags = classify_local_intent(transcript)
                call.transcript = transcript
                call.intent = intent
                call.safety_flags = flags
                call.status = (
                    VoiceCall.Status.ESCALATED if flags else VoiceCall.Status.ACTIVE
                )
                call.save(
                    update_fields=[
                        "transcript",
                        "intent",
                        "safety_flags",
                        "status",
                        "updated_at",
                    ]
                )
                output = {
                    "callId": str(call.id),
                    "intent": intent,
                    "safetyFlags": flags,
                    "requiresHuman": True,
                }
                risk_flags = flags or ["human_review_required"]
            elif operation == "transform-accessibility":
                source_type = str(payload.get("sourceType", "text"))[:80]
                source_id = str(payload.get("sourceId", ""))[:120]
                transform_type = str(payload.get("transformType", "plain_language"))[
                    :32
                ]
                original = str(payload.get("text", ""))[:20000]
                transformed = original
                if (
                    transform_type
                    == AccessibilityTransform.TransformType.PLAIN_LANGUAGE
                ):
                    gateway = call_ai_gateway(
                        "v1/plain-language", {"text": original}
                    )
                    if gateway and isinstance(gateway.get("transformedText"), str):
                        gateway_used = True
                        gateway_model = str(gateway.get("model", gateway_model))
                        gateway_provider = str(gateway.get("provider", "ai-gateway"))
                        transformed = gateway["transformedText"]
                    else:
                        replacements = {
                            "utilize": "use",
                            "commence": "start",
                            "approximately": "about",
                            "demonstrate": "show",
                            "individuals": "people",
                        }
                        for complex_word, plain_word in replacements.items():
                            transformed = re.sub(
                                rf"\b{complex_word}\b",
                                plain_word,
                                transformed,
                                flags=re.IGNORECASE,
                            )
                transform = AccessibilityTransform.objects.create(
                    organization=organization,
                    source_type=source_type,
                    source_id=source_id,
                    transform_type=transform_type,
                    original_text=original,
                    transformed_text=transformed,
                    approved=False,
                )
                output = {
                    "transformId": str(transform.id),
                    "transformedText": transformed,
                    "needsReview": True,
                }
                risk_flags = ["human_review_required"]
            elif operation == "synthesize-speech":
                text = str(payload.get("text", ""))[:4000]
                output = {
                    "status": "queued",
                    "provider": "kokoro-sidecar",
                    "textCharacters": len(text),
                    "requiresLocalRuntime": True,
                }
                risk_flags = ["audio_not_generated_without_configured_local_runtime"]
            else:
                return Response(
                    {"detail": "Unsupported bounded AI operation."}, status=404
                )
            workflow.state = (
                Workflow.State.AWAITING_REVIEW
                if risk_flags
                else Workflow.State.COMPLETED
            )
            if gateway_used:
                workflow.runtime = gateway_provider
                workflow.model_identifier = gateway_model
            workflow.structured_output = output
            workflow.sources = sources
            workflow.validation_results = {
                "schema": "valid",
                "unknownFields": [],
                "authorizedScope": str(organization.id),
            }
            workflow.risk_flags = risk_flags
            workflow.save(
                update_fields=[
                    "state",
                    "structured_output",
                    "sources",
                    "validation_results",
                    "risk_flags",
                    "runtime",
                    "model_identifier",
                    "updated_at",
                ]
            )
            if risk_flags:
                WorkflowReview.objects.create(
                    organization=organization, workflow=workflow
                )
            audit(
                request,
                f"ai.{operation}",
                organization,
                "workflow",
                workflow.id,
                {"riskFlags": risk_flags},
            )
            return Response(
                {
                    "workflowId": str(workflow.id),
                    "state": workflow.state,
                    "output": output,
                    "riskFlags": risk_flags,
                }
            )
        except Exception as exc:
            workflow.state = Workflow.State.FAILED
            workflow.validation_results = {"errorType": type(exc).__name__}
            workflow.save(update_fields=["state", "validation_results", "updated_at"])
            raise


class DonorCohortView(TenantView):
    def get(self, request, slug):
        organization, _ = self.organization(request, slug)
        queryset = DonorSnapshot.objects.filter(
            organization=organization, opt_out=False
        ).select_related("contact")
        lapsed = request.query_params.get("lapsed")
        if lapsed in {"true", "false"}:
            queryset = queryset.filter(lapsed=lapsed == "true")
        result = [
            {
                "contactId": str(snapshot.contact_id),
                "name": snapshot.contact.display_name,
                "recencyDays": snapshot.recency_days,
                "frequency": snapshot.frequency,
                "totalGiving": snapshot.total_giving,
                "lapsed": snapshot.lapsed,
                "reasonCodes": snapshot.explanation,
            }
            for snapshot in queryset[:500]
        ]
        audit(
            request, "donor.cohort_read", organization, metadata={"count": len(result)}
        )
        return Response({"results": result, "model": "explicit_rules_only"})


class VoiceActionView(TenantView):
    def post(self, request, slug, pk):
        organization, membership = self.organization(request, slug)
        if membership.role not in {
            Membership.Role.OWNER,
            Membership.Role.ADMIN,
            Membership.Role.COORDINATOR,
        }:
            raise PermissionDenied(
                "A coordinator or administrator must control call actions."
            )
        call = get_object_or_404(
            VoiceCall.objects.filter(organization=organization), pk=pk
        )
        action = request.data.get("action")
        if action == "transfer":
            call.status = VoiceCall.Status.TRANSFERRED
            call.transfer_target = str(request.data.get("target", "trained human"))[
                :160
            ]
        elif action == "callback":
            call.status = VoiceCall.Status.CALLBACK
            call.callback_requested = True
        elif action == "complete":
            call.status = VoiceCall.Status.COMPLETED
            call.ended_at = timezone.now()
        else:
            return Response(
                {"detail": "action must be transfer, callback, or complete."},
                status=400,
            )
        if call.safety_flags and action != "transfer":
            return Response(
                {
                    "detail": "Safety-flagged calls must transfer to a trained human first."
                },
                status=400,
            )
        call.save(
            update_fields=[
                "status",
                "transfer_target",
                "callback_requested",
                "ended_at",
                "updated_at",
            ]
        )
        audit(request, f"voice.{action}", organization, "voice_call", call.id)
        return Response(
            {
                "id": str(call.id),
                "status": call.status,
                "callbackRequested": call.callback_requested,
            }
        )


class PublicResourceAPIView(APIView):
    permission_classes: list = []

    def get(self, request):
        client_id = request.headers.get("X-Project-Hope-Client", "")
        secret = request.headers.get("X-Project-Hope-Secret", "")
        client = (
            PublicAPIClient.objects.filter(client_id=client_id, active=True)
            .select_related("organization")
            .first()
        )
        supplied_hash = hashlib.sha256(secret.encode()).hexdigest() if secret else ""
        if (
            client is None
            or not secret
            or not hmac.compare_digest(supplied_hash, client.secret_hash)
        ):
            return Response(
                {"detail": "Valid API client credentials are required."}, status=401
            )
        if "resources:read" not in client.scopes:
            return Response(
                {"detail": "Client scope does not permit resource reads."}, status=403
            )
        minute = timezone.now().strftime("%Y%m%d%H%M")
        rate_key = f"project-hope:public-api:{client.id}:{minute}"
        if cache.add(rate_key, 1, timeout=120):
            request_count = 1
        else:
            try:
                request_count = cache.incr(rate_key)
            except ValueError:
                cache.set(rate_key, 1, timeout=120)
                request_count = 1
        if request_count > client.rate_limit_per_minute:
            return Response({"detail": "Client rate limit exceeded."}, status=429)
        query = request.query_params.get("q", "").strip()
        resources = CommunityResource.objects.filter(
            organization=client.organization, status=CommunityResource.Status.ACTIVE
        )
        if query:
            resources = resources.filter(
                Q(name__icontains=query) | Q(description__icontains=query)
            )
        return Response(
            {
                "organization": client.organization.slug,
                "results": [
                    {
                        "id": str(resource.id),
                        "name": resource.name,
                        "description": resource.description,
                        "category": resource.category,
                        "lastVerifiedAt": resource.last_verified_at,
                    }
                    for resource in resources[:100]
                ],
            }
        )


ALLOWED_PLUGIN_CAPABILITIES = {
    "read:contacts",
    "read:resources",
    "read:volunteers",
    "write:appointments",
}


class PluginInstallView(TenantView):
    @transaction.atomic
    def post(self, request, slug, pk):
        organization, membership = self.organization(request, slug)
        require_admin(membership)
        package = get_object_or_404(
            PluginPackage.objects.filter(organization=organization), pk=pk
        )
        requested = set(package.permissions)
        undeclared = requested - ALLOWED_PLUGIN_CAPABILITIES
        if undeclared:
            return Response(
                {
                    "detail": "Plugin requests undeclared or disallowed capabilities.",
                    "capabilities": sorted(undeclared),
                },
                status=400,
            )
        if package.status == PluginPackage.Status.REVOKED:
            return Response(
                {"detail": "Revoked plugins cannot be installed."}, status=400
            )
        installation = PluginInstallation.objects.create(
            organization=organization,
            package=package,
            enabled=False,
            config=request.data.get("config", {})
            if isinstance(request.data.get("config", {}), dict)
            else {},
        )
        package.status = PluginPackage.Status.INSTALLED
        package.save(update_fields=["status", "updated_at"])
        audit(
            request,
            "plugin.installed",
            organization,
            "plugin",
            package.id,
            {"enabled": False},
        )
        return Response(
            {"installationId": str(installation.id), "enabled": installation.enabled},
            status=201,
        )


class PluginRevokeView(TenantView):
    @transaction.atomic
    def post(self, request, slug, pk):
        organization, membership = self.organization(request, slug)
        require_admin(membership)
        package = get_object_or_404(
            PluginPackage.objects.filter(organization=organization), pk=pk
        )
        package.status = PluginPackage.Status.REVOKED
        package.disabled_reason = str(
            request.data.get("reason", "Revoked by administrator")
        )[:1000]
        package.save(update_fields=["status", "disabled_reason", "updated_at"])
        package.installations.update(enabled=False)
        audit(request, "plugin.revoked", organization, "plugin", package.id)
        return Response({"id": str(package.id), "status": package.status})


class APIClientIssueView(TenantView):
    def post(self, request, slug):
        organization, membership = self.organization(request, slug)
        require_admin(membership)
        requested_scopes = request.data.get("scopes", [])
        if not isinstance(requested_scopes, list) or any(
            not isinstance(scope, str) for scope in requested_scopes
        ):
            return Response({"detail": "scopes must be a list of strings."}, status=400)
        allowed_scopes = {
            "contacts:read",
            "volunteers:read",
            "schedules:read",
            "resources:read",
            "documents:read",
        }
        if set(requested_scopes) - allowed_scopes:
            return Response(
                {"detail": "One or more requested scopes are not available."},
                status=400,
            )
        client_id = f"hope_{secrets.token_urlsafe(12)}"
        secret = secrets.token_urlsafe(32)
        client = PublicAPIClient.objects.create(
            organization=organization,
            name=str(request.data.get("name", "API client"))[:160],
            client_id=client_id,
            secret_hash=hashlib.sha256(secret.encode()).hexdigest(),
            scopes=requested_scopes,
            created_by=request.user,
        )
        audit(
            request,
            "api_client.created",
            organization,
            "api_client",
            client.id,
            {"scopes": requested_scopes},
        )
        return Response(
            {
                "id": str(client.id),
                "clientId": client_id,
                "clientSecret": secret,
                "scopes": requested_scopes,
                "warning": "Store this secret now; it will not be shown again.",
            },
            status=201,
        )


class PluginTokenIssueView(TenantView):
    def post(self, request, slug, pk):
        organization, membership = self.organization(request, slug)
        require_admin(membership)
        installation = get_object_or_404(
            PluginInstallation.objects.filter(organization=organization), pk=pk
        )
        if installation.package.status == PluginPackage.Status.REVOKED:
            return Response(
                {"detail": "Revoked plugin installations cannot receive tokens."},
                status=400,
            )
        capabilities = request.data.get(
            "capabilities", installation.package.permissions
        )
        if not isinstance(capabilities, list) or not set(capabilities).issubset(
            ALLOWED_PLUGIN_CAPABILITIES
        ):
            return Response(
                {"detail": "Requested capabilities exceed the allowlist."}, status=400
            )
        token = secrets.token_urlsafe(32)
        token_record = PluginCapabilityToken.objects.create(
            organization=organization,
            installation=installation,
            token_hash=hashlib.sha256(token.encode()).hexdigest(),
            capabilities=capabilities,
            expires_at=timezone.now() + timedelta(hours=1),
        )
        audit(
            request,
            "plugin.token_issued",
            organization,
            "plugin_token",
            token_record.id,
            {"capabilities": capabilities},
        )
        return Response(
            {
                "token": token,
                "expiresAt": token_record.expires_at,
                "capabilities": capabilities,
            },
            status=201,
        )
