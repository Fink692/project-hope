import json
from datetime import timedelta
from io import StringIO
from urllib.parse import parse_qs, urlparse
from unittest.mock import patch

from django.core import mail
from django.core.cache import cache
from django.core import management
from django.core.exceptions import ValidationError
from django.test import TestCase, override_settings
from django.utils import timezone
from rest_framework.authtoken.models import Token
from rest_framework.test import APIClient

from audit.models import AuditEvent

from .models import Membership, Organization, PilotApplication, User


class FoundationApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.alice = User.objects.create_user("alice@example.org", "Alice-password-123")
        self.bob = User.objects.create_user("bob@example.org", "Bob-password-123")
        self.charity_a = Organization.objects.create(
            name="Alpha Charity", slug="alpha-charity"
        )
        self.charity_b = Organization.objects.create(
            name="Beta Charity", slug="beta-charity"
        )
        self.alice_a = Membership.objects.create(
            user=self.alice,
            organization=self.charity_a,
            role=Membership.Role.OWNER,
        )
        Membership.objects.create(
            user=self.alice,
            organization=self.charity_b,
            role=Membership.Role.VIEWER,
        )
        Membership.objects.create(
            user=self.bob,
            organization=self.charity_b,
            role=Membership.Role.OWNER,
        )

    def login(self, email="alice@example.org", password="Alice-password-123"):
        response = self.client.post(
            "/api/v1/auth/login/",
            {"email": email, "password": password},
            format="json",
        )
        self.assertEqual(response.status_code, 200, response.content)

    def test_health_is_public_and_reports_database(self):
        response = self.client.get("/api/v1/healthz/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "ok")
        self.assertEqual(response.json()["database"], "ok")

    def test_login_me_and_logout(self):
        self.login()

        me = self.client.get("/api/v1/me/")
        self.assertEqual(me.status_code, 200)
        self.assertEqual(me.json()["user"]["email"], "alice@example.org")
        self.assertEqual(len(me.json()["organizations"]), 2)

        logout = self.client.post("/api/v1/auth/logout/", {}, format="json")
        self.assertEqual(logout.status_code, 200)
        self.assertIn(AuditEvent.objects.filter(action="auth.logout").count(), (1,))

        unauthenticated = self.client.get("/api/v1/me/")
        self.assertIn(unauthenticated.status_code, (401, 403))

    def test_login_issues_token_and_logout_revokes_it(self):
        response = self.client.post(
            "/api/v1/auth/login/",
            {"email": "alice@example.org", "password": "Alice-password-123"},
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        token = response.json()["token"]
        self.assertTrue(Token.objects.filter(user=self.alice, key=token).exists())

        token_client = APIClient()
        token_client.credentials(HTTP_AUTHORIZATION=f"Token {token}")
        self.assertEqual(token_client.get("/api/v1/me/").status_code, 200)

        self.client.force_authenticate(user=self.alice)
        self.assertEqual(
            self.client.post("/api/v1/auth/logout/", {}, format="json").status_code,
            200,
        )
        self.assertEqual(token_client.get("/api/v1/me/").status_code, 401)

    def test_user_can_create_organization_and_becomes_owner(self):
        self.login()

        response = self.client.post(
            "/api/v1/organizations/",
            {"name": "New Hope Services"},
            format="json",
        )

        self.assertEqual(response.status_code, 201, response.content)
        organization = Organization.objects.get(slug="new-hope-services")
        self.assertTrue(
            Membership.objects.filter(
                organization=organization,
                user=self.alice,
                role=Membership.Role.OWNER,
                active=True,
            ).exists()
        )
        self.assertTrue(
            AuditEvent.objects.filter(
                action="organization.created", organization=organization
            ).exists()
        )

    def test_cross_tenant_access_is_not_revealed(self):
        self.login()

        organization = self.client.get("/api/v1/organizations/beta-charity/")
        self.assertEqual(organization.status_code, 200)

        Membership.objects.filter(user=self.alice, organization=self.charity_b).update(
            active=False
        )
        hidden_organization = self.client.get("/api/v1/organizations/beta-charity/")
        hidden_audit = self.client.get(
            "/api/v1/organizations/beta-charity/audit-events/"
        )
        self.assertEqual(hidden_organization.status_code, 404)
        self.assertEqual(hidden_audit.status_code, 404)

    def test_viewer_cannot_update_organization_or_read_audit(self):
        self.login()
        Membership.objects.filter(user=self.alice, organization=self.charity_a).update(
            role=Membership.Role.VIEWER
        )

        update = self.client.patch(
            "/api/v1/organizations/alpha-charity/",
            {"name": "Changed"},
            format="json",
        )
        audit = self.client.get("/api/v1/organizations/alpha-charity/audit-events/")
        self.assertEqual(update.status_code, 403)
        self.assertEqual(audit.status_code, 403)

    def test_owner_can_add_member_and_audit_is_visible(self):
        self.login()

        response = self.client.post(
            "/api/v1/organizations/alpha-charity/members/",
            {"email": "bob@example.org", "role": "staff"},
            format="json",
        )
        self.assertEqual(response.status_code, 201, response.content)
        self.assertTrue(
            Membership.objects.filter(
                organization=self.charity_a,
                user=self.bob,
                role=Membership.Role.STAFF,
            ).exists()
        )
        audit = self.client.get("/api/v1/organizations/alpha-charity/audit-events/")
        self.assertEqual(audit.status_code, 200)
        self.assertTrue(
            any(event["action"] == "membership.created" for event in audit.json())
        )

    def test_an_admin_cannot_assign_owner(self):
        Membership.objects.filter(user=self.alice, organization=self.charity_a).update(
            role=Membership.Role.ADMIN
        )
        self.login()

        response = self.client.post(
            "/api/v1/organizations/alpha-charity/members/",
            {"email": "bob@example.org", "role": "owner"},
            format="json",
        )
        self.assertEqual(response.status_code, 403)

    def test_an_admin_cannot_change_an_owner_membership(self):
        Membership.objects.filter(user=self.alice, organization=self.charity_a).update(
            role=Membership.Role.ADMIN
        )
        other_owner = Membership.objects.create(
            organization=self.charity_a,
            user=self.bob,
            role=Membership.Role.OWNER,
        )
        self.login()

        response = self.client.patch(
            f"/api/v1/organizations/alpha-charity/members/{other_owner.id}/",
            {"role": "staff"},
            format="json",
        )
        self.assertEqual(response.status_code, 403)

    def test_audit_events_are_append_only(self):
        event = AuditEvent.objects.record(action="test.event", actor=self.alice)

        event.action = "changed"
        with self.assertRaises(ValidationError):
            event.save()
        with self.assertRaises(ValidationError):
            event.delete()


class SeedCommandTests(TestCase):
    def test_seed_demo_is_idempotent(self):
        management.call_command("seed_demo", verbosity=0)
        management.call_command("seed_demo", verbosity=0)

        self.assertEqual(User.objects.filter(email="demo@example.org").count(), 1)
        self.assertEqual(Organization.objects.filter(slug="hope-demo").count(), 1)
        self.assertEqual(
            Membership.objects.filter(organization__slug="hope-demo").count(), 1
        )


@override_settings(
    EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
    PROJECT_HOPE_PUBLIC_URL="https://hope.example.org",
)
class PilotApplicationApiTests(TestCase):
    def setUp(self):
        cache.clear()
        self.client = APIClient()
        self.payload = {
            "contact_name": "Amina Hope",
            "email": "AMINA@EXAMPLE.ORG",
            "organization_name": "North Star Community Centre",
            "website": "https://north-star.example.org",
            "country_or_region": "Manitoba, Canada",
            "team_size": "6-20",
            "primary_need": "volunteers",
            "plan_interest": "founding_partner",
            "notes": "We coordinate 80 active volunteers.",
            "consent_to_contact": True,
            "source": "linkedin",
            "utm_source": "linkedin",
            "utm_medium": "social",
            "utm_campaign": "founding-10",
            "referrer": "https://www.linkedin.com/",
            "company_website": "",
        }

    def submit(self, **overrides):
        return self.client.post(
            "/api/v1/pilot-applications/",
            {**self.payload, **overrides},
            format="json",
        )

    def verification_token(self):
        link = next(
            line
            for line in mail.outbox[-1].body.splitlines()
            if line.startswith("https://")
        )
        parsed = urlparse(link)
        self.assertEqual(parsed.query, "")
        return parse_qs(parsed.fragment)["pilot_token"][0]

    def test_application_is_captured_normalized_and_verifiable(self):
        response = self.submit()

        self.assertEqual(response.status_code, 202, response.content)
        self.assertEqual(
            response.json(),
            {
                "detail": (
                    "Application received. Check your email to confirm your request."
                )
            },
        )
        application = PilotApplication.objects.get()
        self.assertEqual(application.email, "amina@example.org")
        self.assertEqual(application.source, PilotApplication.Source.LINKEDIN)
        self.assertEqual(application.privacy_version, PilotApplication.PRIVACY_VERSION)
        self.assertIsNone(application.verified_at)
        self.assertEqual(application.verification_email_attempts, 1)
        self.assertIsNotNone(application.verification_email_sent_at)
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, ["amina@example.org"])

        verified = self.client.post(
            "/api/v1/pilot-applications/verify/",
            {"token": self.verification_token()},
            format="json",
        )

        self.assertEqual(verified.status_code, 200, verified.content)
        application.refresh_from_db()
        self.assertIsNotNone(application.verified_at)

    def test_duplicate_submission_is_private_and_does_not_overwrite_lead(self):
        first = self.submit()
        second = self.submit(
            contact_name="Someone Else",
            organization_name="Overwrite Attempt",
            email="amina@example.org",
        )

        self.assertEqual(first.status_code, 202)
        self.assertEqual(second.status_code, 202)
        self.assertEqual(first.json(), second.json())
        self.assertEqual(PilotApplication.objects.count(), 1)
        application = PilotApplication.objects.get()
        self.assertEqual(application.contact_name, "Amina Hope")
        self.assertEqual(application.organization_name, "North Star Community Centre")
        self.assertEqual(application.submission_count, 2)
        self.assertEqual(len(mail.outbox), 1)

    def test_verified_duplicate_does_not_send_more_mail(self):
        self.submit()
        self.client.post(
            "/api/v1/pilot-applications/verify/",
            {"token": self.verification_token()},
            format="json",
        )

        response = self.submit(email="amina@example.org")

        self.assertEqual(response.status_code, 202)
        self.assertEqual(len(mail.outbox), 1)

    def test_consent_is_explicitly_required(self):
        rejected = self.submit(consent_to_contact=False)
        missing_payload = dict(self.payload)
        missing_payload.pop("consent_to_contact")
        missing = self.client.post(
            "/api/v1/pilot-applications/", missing_payload, format="json"
        )

        self.assertEqual(rejected.status_code, 400)
        self.assertEqual(missing.status_code, 400)
        self.assertEqual(PilotApplication.objects.count(), 0)

    def test_honeypot_returns_generic_success_without_storing_data(self):
        response = self.submit(company_website="https://spam.example")

        self.assertEqual(response.status_code, 202)
        self.assertEqual(PilotApplication.objects.count(), 0)
        self.assertEqual(len(mail.outbox), 0)

    def test_invalid_verification_token_is_rejected(self):
        response = self.client.post(
            "/api/v1/pilot-applications/verify/",
            {"token": "not-a-signed-token"},
            format="json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertFalse(response.json().get("verified", False))

    def test_failed_confirmation_mail_is_recorded_and_retried(self):
        with self.assertLogs("identity.pilot", level="ERROR"):
            with patch("identity.pilot.send_mail", side_effect=OSError("relay down")):
                response = self.submit()

        self.assertEqual(response.status_code, 202)
        application = PilotApplication.objects.get()
        self.assertEqual(application.verification_email_attempts, 1)
        self.assertIsNone(application.verification_email_sent_at)
        PilotApplication.objects.filter(id=application.id).update(
            verification_email_last_attempt_at=timezone.now() - timedelta(minutes=16)
        )
        output = StringIO()

        management.call_command("retry_pilot_verification_emails", stdout=output)

        application.refresh_from_db()
        self.assertEqual(json.loads(output.getvalue())["delivered"], 1)
        self.assertEqual(application.verification_email_attempts, 2)
        self.assertIsNotNone(application.verification_email_sent_at)
        self.assertEqual(len(mail.outbox), 1)

    def test_metrics_are_admin_only_and_contain_no_personal_data(self):
        PilotApplication.objects.create(
            contact_name="Verified Contact",
            email="verified@example.org",
            organization_name="Verified Charity",
            team_size="2-5",
            primary_need="operations",
            plan_interest="founding_partner",
            consent_to_contact=True,
            verified_at=timezone.now(),
            status=PilotApplication.Status.QUALIFIED,
        )
        PilotApplication.objects.create(
            contact_name="Pending Contact",
            email="pending@example.org",
            organization_name="Pending Charity",
            team_size="1",
            primary_need="impact",
            plan_interest="community",
            consent_to_contact=True,
        )

        unauthorized = self.client.get("/api/v1/pilot-applications/metrics/")
        self.assertIn(unauthorized.status_code, (401, 403))
        admin = User.objects.create_superuser("admin@example.org", "Admin-password-123")
        self.client.force_authenticate(user=admin)
        response = self.client.get("/api/v1/pilot-applications/metrics/")

        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual(response.json()["verified"], 1)
        self.assertEqual(response.json()["qualified"], 1)
        self.assertEqual(response.json()["remaining"], 9)
        serialized = json.dumps(response.json())
        self.assertNotIn("verified@example.org", serialized)
        self.assertNotIn("Verified Contact", serialized)

    def test_pilot_metrics_command_reports_verified_people_only(self):
        PilotApplication.objects.create(
            contact_name="Pilot Contact",
            email="pilot@example.org",
            organization_name="Pilot Charity",
            team_size="2-5",
            primary_need="operations",
            plan_interest="founding_partner",
            consent_to_contact=True,
            verified_at=timezone.now(),
            status=PilotApplication.Status.PILOT,
        )
        output = StringIO()

        management.call_command("pilot_metrics", stdout=output)

        metrics = json.loads(output.getvalue())
        self.assertEqual(metrics["verified"], 1)
        self.assertEqual(metrics["active_pilots"], 1)
        self.assertEqual(metrics["remaining"], 9)

    def test_retention_command_previews_then_purges_only_expired_applications(self):
        old = timezone.now() - timedelta(days=400)
        expired = PilotApplication.objects.create(
            contact_name="Expired Contact",
            email="expired@example.org",
            organization_name="Expired Charity",
            team_size="1",
            primary_need="operations",
            plan_interest="community",
            consent_to_contact=True,
        )
        active = PilotApplication.objects.create(
            contact_name="Active Pilot",
            email="active@example.org",
            organization_name="Active Charity",
            team_size="2-5",
            primary_need="operations",
            plan_interest="founding_partner",
            consent_to_contact=True,
            verified_at=old,
            status=PilotApplication.Status.PILOT,
        )
        PilotApplication.objects.filter(id__in=[expired.id, active.id]).update(
            created_at=old, updated_at=old
        )
        preview_output = StringIO()

        management.call_command("purge_pilot_applications", stdout=preview_output)

        self.assertEqual(json.loads(preview_output.getvalue())["matched"], 1)
        self.assertEqual(PilotApplication.objects.count(), 2)

        execute_output = StringIO()
        management.call_command(
            "purge_pilot_applications", execute=True, stdout=execute_output
        )

        self.assertEqual(json.loads(execute_output.getvalue())["deleted"], 1)
        self.assertFalse(PilotApplication.objects.filter(id=expired.id).exists())
        self.assertTrue(PilotApplication.objects.filter(id=active.id).exists())
