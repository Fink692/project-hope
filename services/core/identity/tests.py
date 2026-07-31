from django.core import management
from django.core.exceptions import ValidationError
from django.test import TestCase
from rest_framework.authtoken.models import Token
from rest_framework.test import APIClient

from audit.models import AuditEvent

from .models import Membership, Organization, User


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
