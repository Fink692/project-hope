from datetime import timedelta
from unittest.mock import patch
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from identity.models import Membership, Organization, User

from .models import (
    AccessibilityTransform,
    Contact,
    EmailDraft,
    PluginPackage,
    PublicAPIClient,
    RetentionPolicy,
    ScheduleEvent,
    VoiceCall,
    VolunteerApplication,
    VolunteerProfile,
    Workflow,
)


class CompleteRoadmapApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            "coordinator@example.org", "Coordinator-password-123"
        )
        self.other_user = User.objects.create_user(
            "other@example.org", "Other-password-123"
        )
        self.organization = Organization.objects.create(
            name="Roadmap Charity", slug="roadmap-charity"
        )
        self.other_organization = Organization.objects.create(
            name="Other Charity", slug="other-charity"
        )
        Membership.objects.create(
            user=self.user,
            organization=self.organization,
            role=Membership.Role.OWNER,
        )
        Membership.objects.create(
            user=self.other_user,
            organization=self.other_organization,
            role=Membership.Role.OWNER,
        )
        self.assertTrue(
            self.client.login(
                email=self.user.email, password="Coordinator-password-123"
            )
        )

    def post(self, path, data, format="json"):
        response = self.client.post(path, data, format=format)
        self.assertLess(response.status_code, 300, response.content)
        return response

    def test_crm_and_tenant_scoping(self):
        contact = self.post(
            "/api/v1/organizations/roadmap-charity/contacts/",
            {"first_name": "Amina", "last_name": "Hope", "email": "amina@example.org"},
        ).json()
        self.assertEqual(contact["display_name"], "Amina Hope")
        listing = self.client.get("/api/v1/organizations/roadmap-charity/contacts/")
        self.assertEqual(listing.status_code, 200)
        self.assertEqual(len(listing.json()), 1)
        hidden = self.client.get("/api/v1/organizations/other-charity/contacts/")
        self.assertEqual(hidden.status_code, 404)

        foreign_contact = Contact.objects.create(
            organization=self.other_organization,
            first_name="Foreign",
            email="foreign@example.org",
        )
        relation = self.client.post(
            "/api/v1/organizations/roadmap-charity/relationships/",
            {
                "from_contact": contact["id"],
                "to_contact": str(foreign_contact.id),
                "relation_type": "family",
            },
            format="json",
        )
        self.assertEqual(relation.status_code, 400)

    def test_admin_only_registry_is_not_visible_to_viewers(self):
        Membership.objects.filter(
            user=self.user, organization=self.organization
        ).update(role=Membership.Role.VIEWER)
        response = self.client.get("/api/v1/organizations/roadmap-charity/ai-models/")
        self.assertEqual(response.status_code, 403)
        retention = self.client.get(
            "/api/v1/organizations/roadmap-charity/retention-policies/"
        )
        self.assertEqual(retention.status_code, 403)

    @patch(
        "modules.views.call_ai_gateway",
        return_value={
            "intent": "appointment",
            "riskFlags": ["human_review_required"],
            "requiresHuman": True,
        },
    )
    def test_ai_workflow_uses_configured_gateway_boundary(self, gateway):
        response = self.post(
            "/api/v1/organizations/roadmap-charity/ai/v1/classify-intent/",
            {"text": "I need to book an appointment."},
        )
        workflow = Workflow.objects.get(pk=response.json()["workflowId"])
        self.assertEqual(response.json()["output"]["confidence"], "gateway-bounded")
        self.assertEqual(workflow.runtime, "ai-gateway")
        gateway.assert_called_once_with(
            "v1/classify-intent", {"text": "I need to book an appointment."}
        )

    def test_documents_search_and_extraction(self):
        document = self.post(
            "/api/v1/organizations/roadmap-charity/documents/",
            {
                "title": "Office policy",
                "file": SimpleUploadedFile(
                    "office.txt",
                    b"Office hours are Monday to Friday. Contact the coordinator for an appointment.",
                    content_type="text/plain",
                ),
            },
            format="multipart",
        ).json()
        extraction = self.post(
            "/api/v1/organizations/roadmap-charity/ai/v1/extract-document/",
            {"documentId": document["id"]},
        ).json()
        self.assertEqual(extraction["state"], Workflow.State.COMPLETED)
        search = self.client.get(
            "/api/v1/organizations/roadmap-charity/documents/search/?q=office+hours"
        )
        self.assertEqual(search.status_code, 200)
        self.assertEqual(len(search.json()["passages"]), 1)
        self.assertEqual(search.json()["passages"][0]["pageNumber"], None)

    def test_documents_reject_unsafe_upload_types(self):
        response = self.client.post(
            "/api/v1/organizations/roadmap-charity/documents/",
            {
                "title": "Executable",
                "file": SimpleUploadedFile(
                    "program.exe",
                    b"not a document",
                    content_type="application/x-msdownload",
                ),
            },
            format="multipart",
        )
        self.assertEqual(response.status_code, 415)

        malformed_office = self.client.post(
            "/api/v1/organizations/roadmap-charity/documents/",
            {
                "title": "Malformed office file",
                "file": SimpleUploadedFile(
                    "broken.docx",
                    b"not a zip archive",
                    content_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                ),
            },
            format="multipart",
        )
        self.assertEqual(malformed_office.status_code, 415)

    def test_legal_hold_blocks_direct_record_deletion(self):
        contact = self.post(
            "/api/v1/organizations/roadmap-charity/contacts/",
            {"first_name": "Held", "last_name": "Record"},
        ).json()
        RetentionPolicy.objects.create(
            organization=self.organization,
            record_type="contacts",
            retention_days=365,
            legal_hold=True,
        )
        response = self.client.delete(
            f"/api/v1/organizations/roadmap-charity/contacts/{contact['id']}/"
        )
        self.assertEqual(response.status_code, 423)
        self.assertTrue(Contact.objects.filter(pk=contact["id"]).exists())

    def test_scheduling_and_ical_export(self):
        starts = timezone.now() + timedelta(days=1)
        event = self.post(
            "/api/v1/organizations/roadmap-charity/schedules/",
            {
                "title": "Volunteer orientation",
                "event_type": "meeting",
                "starts_at": starts.isoformat(),
                "ends_at": (starts + timedelta(hours=1)).isoformat(),
            },
        ).json()
        self.assertEqual(
            ScheduleEvent.objects.get(pk=event["id"]).title, "Volunteer orientation"
        )
        calendar = self.client.get(
            "/api/v1/organizations/roadmap-charity/schedules/ical/"
        )
        self.assertEqual(calendar.status_code, 200)
        self.assertIn("BEGIN:VCALENDAR", calendar.content.decode())
        self.assertIn("Volunteer orientation", calendar.content.decode())

    def test_volunteer_pipeline_promotes_only_after_human_review(self):
        application = self.post(
            "/api/v1/organizations/roadmap-charity/volunteer-applications/",
            {
                "applicant_name": "Sam Volunteer",
                "email": "sam@example.org",
                "skills": ["food service"],
                "interests": ["community meals"],
                "availability": {"monday": ["09:00-12:00"]},
            },
        ).json()
        pipeline = self.client.get(
            "/api/v1/organizations/roadmap-charity/volunteers/pipeline/"
        )
        self.assertEqual(pipeline.status_code, 200)
        self.assertEqual(pipeline.json()["applications"][0]["status"], "received")
        review = self.post(
            f"/api/v1/organizations/roadmap-charity/volunteer-applications/{application['id']}/review/",
            {"status": "accepted"},
        ).json()
        self.assertEqual(review["status"], VolunteerApplication.Status.ACCEPTED)
        self.assertTrue(
            VolunteerProfile.objects.filter(
                pk=review["volunteerProfileId"], status="active"
            ).exists()
        )

    def test_grant_accessibility_voice_and_metrics_records_are_scoped(self):
        grant = self.post(
            "/api/v1/organizations/roadmap-charity/grants/",
            {
                "name": "Community grant",
                "funder": "Local foundation",
                "status": "in_progress",
            },
        ).json()
        question = self.post(
            "/api/v1/organizations/roadmap-charity/grant-questions/",
            {"workspace": grant["id"], "question": "What changed?"},
        ).json()
        self.assertEqual(question["status"], "open")
        transform = self.post(
            "/api/v1/organizations/roadmap-charity/accessibility-transforms/",
            {
                "source_type": "grant_question",
                "source_id": question["id"],
                "transform_type": "plain_language",
                "original_text": "The programme demonstrates measurable impact.",
                "transformed_text": "The programme shows its results.",
            },
        ).json()
        self.assertEqual(
            transform["transform_type"],
            AccessibilityTransform.TransformType.PLAIN_LANGUAGE,
        )
        call = self.post(
            "/api/v1/organizations/roadmap-charity/calls/",
            {
                "external_id": "call-1",
                "started_at": timezone.now().isoformat(),
                "consent_captured": True,
            },
        ).json()
        transcribed = self.post(
            "/api/v1/organizations/roadmap-charity/ai/v1/transcribe/",
            {"callId": call["id"], "transcript": "I need an appointment."},
        ).json()
        self.assertEqual(transcribed["output"]["intent"], "appointment")
        self.assertEqual(VoiceCall.objects.get(pk=call["id"]).intent, "appointment")
        metric = self.post(
            "/api/v1/organizations/roadmap-charity/metrics/",
            {
                "key": "reach",
                "name": "Programme reach",
                "definition": "Unique contacts served.",
            },
        ).json()
        self.post(
            "/api/v1/organizations/roadmap-charity/metric-snapshots/",
            {
                "metric": metric["id"],
                "period_start": "2026-01-01",
                "period_end": "2026-06-30",
                "value": "12",
            },
        )
        summary = self.client.get(
            "/api/v1/organizations/roadmap-charity/metrics/summary/"
        )
        self.assertEqual(summary.json()["metrics"][0]["value"], 12.0)

    def test_bounded_ai_review_and_translation(self):
        intent = self.post(
            "/api/v1/organizations/roadmap-charity/ai/v1/classify-intent/",
            {"text": "I need emergency help"},
        ).json()
        self.assertEqual(intent["state"], Workflow.State.AWAITING_REVIEW)
        self.assertIn("human_transfer", intent["output"]["intent"])
        review = self.post(
            f"/api/v1/organizations/roadmap-charity/workflows/{intent['workflowId']}/review/",
            {"decision": "approved", "comments": "Escalated to a trained human."},
        ).json()
        self.assertEqual(review["state"], Workflow.State.APPROVED)

        translation = self.post(
            "/api/v1/organizations/roadmap-charity/ai/v1/translate-segments/",
            {
                "sourceLanguage": "en",
                "targetLanguage": "fr",
                "text": "Hello, thank you for your help.",
            },
        ).json()
        self.assertEqual(translation["state"], Workflow.State.AWAITING_REVIEW)
        self.assertIn("bonjour", translation["output"]["translatedText"].lower())

    def test_email_drafting_requires_approval_and_smtp(self):
        mailbox = self.post(
            "/api/v1/organizations/roadmap-charity/mailboxes/",
            {"name": "Shared inbox", "address": "hello@example.org"},
        ).json()
        message = self.post(
            "/api/v1/organizations/roadmap-charity/messages/",
            {
                "mailbox": mailbox["id"],
                "external_id": "msg-1",
                "sender": "visitor@example.org",
                "recipients": ["hello@example.org"],
                "subject": "Appointment request",
                "body_excerpt": "Can I book an appointment?",
                "received_at": timezone.now().isoformat(),
            },
        ).json()
        draft_workflow = self.post(
            "/api/v1/organizations/roadmap-charity/ai/v1/draft-email/",
            {"messageId": message["id"]},
        ).json()
        draft = EmailDraft.objects.get(pk=draft_workflow["output"]["draftId"])
        self.assertEqual(draft.status, EmailDraft.Status.DRAFT)
        approval = self.post(
            f"/api/v1/organizations/roadmap-charity/email-drafts/{draft.id}/approval/",
            {"action": "approve"},
        ).json()
        self.assertEqual(approval["status"], EmailDraft.Status.APPROVED)
        send = self.client.post(
            f"/api/v1/organizations/roadmap-charity/email-drafts/{draft.id}/send/",
            {},
            format="json",
        )
        self.assertIn(send.status_code, (200, 503))
        if send.status_code == 503:
            self.assertIn("SMTP_HOST", send.json()["detail"])
        else:
            self.assertEqual(send.json()["status"], EmailDraft.Status.SENT)

    def test_resources_metrics_donors_and_plugins(self):
        resource = self.post(
            "/api/v1/organizations/roadmap-charity/resources/",
            {
                "name": "Community food support",
                "description": "Food support and referral help.",
                "category": "food",
                "languages": ["en", "fr"],
                "status": "active",
                "last_verified_at": timezone.now().isoformat(),
            },
        ).json()
        resource_search = self.client.get(
            "/api/v1/organizations/roadmap-charity/resources/search/?q=food&language=fr"
        )
        self.assertEqual(resource_search.status_code, 200)
        self.assertEqual(resource_search.json()["results"][0]["id"], resource["id"])

        contact = self.post(
            "/api/v1/organizations/roadmap-charity/contacts/",
            {"first_name": "Donor", "contact_type": "donor"},
        ).json()
        donor = self.post(
            "/api/v1/organizations/roadmap-charity/donor-snapshots/",
            {
                "contact": contact["id"],
                "period_start": "2026-01-01",
                "period_end": "2026-06-30",
                "recency_days": 240,
                "frequency": 2,
                "total_giving": "100.00",
                "lapsed": True,
                "explanation": ["recency_over_180_days"],
            },
        ).json()
        cohort = self.client.get(
            "/api/v1/organizations/roadmap-charity/donors/cohort/?lapsed=true"
        )
        self.assertEqual(cohort.status_code, 200)
        self.assertEqual(cohort.json()["results"][0]["contactId"], donor["contact"])

        package = self.post(
            "/api/v1/organizations/roadmap-charity/plugins/",
            {
                "name": "Resource export",
                "version": "1.0.0",
                "publisher": "Project Hope community",
                "permissions": ["read:resources"],
                "manifest": {
                    "apiVersion": "v1",
                    "entrypoint": "https://example.invalid/plugin",
                },
            },
        ).json()
        installation = self.post(
            f"/api/v1/organizations/roadmap-charity/plugins/{package['id']}/install/",
            {},
        ).json()
        self.assertFalse(installation["enabled"])
        revoked = self.post(
            f"/api/v1/organizations/roadmap-charity/plugins/{package['id']}/revoke/",
            {"reason": "test"},
        ).json()
        self.assertEqual(revoked["status"], PluginPackage.Status.REVOKED)

    def test_public_api_and_review_gates(self):
        resource = self.post(
            "/api/v1/organizations/roadmap-charity/resources/",
            {
                "name": "Verified service",
                "description": "A verified local service.",
                "category": "support",
                "status": "active",
                "last_verified_at": timezone.now().isoformat(),
            },
        ).json()
        client = self.post(
            "/api/v1/organizations/roadmap-charity/developer/api-clients/issue/",
            {"name": "Public directory", "scopes": ["resources:read"]},
        ).json()
        self.assertTrue(
            PublicAPIClient.objects.filter(client_id=client["clientId"]).exists()
        )
        public = self.client.get(
            "/api/v1/public/v1/resources/?q=verified",
            HTTP_X_PROJECT_HOPE_CLIENT=client["clientId"],
            HTTP_X_PROJECT_HOPE_SECRET=client["clientSecret"],
        )
        self.assertEqual(public.status_code, 200)
        self.assertEqual(public.json()["results"][0]["id"], resource["id"])
        PublicAPIClient.objects.filter(client_id=client["clientId"]).update(
            rate_limit_per_minute=1
        )
        limited = self.client.get(
            "/api/v1/public/v1/resources/",
            HTTP_X_PROJECT_HOPE_CLIENT=client["clientId"],
            HTTP_X_PROJECT_HOPE_SECRET=client["clientSecret"],
        )
        self.assertEqual(limited.status_code, 429)

        grant = self.post(
            "/api/v1/organizations/roadmap-charity/grants/",
            {"name": "Budget grant", "funder": "Foundation"},
        ).json()
        budget = self.post(
            f"/api/v1/organizations/roadmap-charity/grants/{grant['id']}/validate-budget/",
            {"budget": {"staff": "100.00", "supplies": "25.50"}, "save": True},
        ).json()
        self.assertTrue(budget["valid"])
        self.assertEqual(budget["total"], "125.50")

        translation = self.post(
            "/api/v1/organizations/roadmap-charity/ai/v1/translate-segments/",
            {"sourceLanguage": "en", "targetLanguage": "fr", "text": "Hello"},
        ).json()
        translation_review = self.post(
            f"/api/v1/organizations/roadmap-charity/translations/{translation['output']['jobId']}/review/",
            {"decision": "approved"},
        ).json()
        self.assertEqual(translation_review["status"], "approved")

        transform = self.post(
            "/api/v1/organizations/roadmap-charity/ai/v1/transform-accessibility/",
            {
                "sourceType": "note",
                "sourceId": "1",
                "transformType": "plain_language",
                "text": "Utilize this information.",
            },
        ).json()
        accessibility_review = self.post(
            f"/api/v1/organizations/roadmap-charity/accessibility-transforms/{transform['output']['transformId']}/review/",
            {"approved": True},
        ).json()
        self.assertTrue(accessibility_review["approved"])

        call = self.post(
            "/api/v1/organizations/roadmap-charity/calls/",
            {
                "external_id": "safety-call",
                "started_at": timezone.now().isoformat(),
                "safety_flags": ["emergency"],
            },
        ).json()
        blocked = self.client.post(
            f"/api/v1/organizations/roadmap-charity/calls/{call['id']}/action/",
            {"action": "callback"},
            format="json",
        )
        self.assertEqual(blocked.status_code, 400)
        transferred = self.post(
            f"/api/v1/organizations/roadmap-charity/calls/{call['id']}/action/",
            {"action": "transfer", "target": "on-call coordinator"},
        ).json()
        self.assertEqual(transferred["status"], "transferred")
