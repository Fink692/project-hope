import json
from datetime import timedelta
from io import StringIO
from urllib.parse import parse_qs, urlparse
from unittest.mock import patch

from django.conf import settings
from django.core import mail
from django.core.cache import cache
from django.core import management
from django.core.exceptions import ValidationError
from django.test import TestCase, override_settings
from django.utils import timezone
from rest_framework.authtoken.models import Token
from rest_framework.test import APIClient, APIRequestFactory
from rest_framework.throttling import ScopedRateThrottle

from audit.models import AuditEvent

from .invitations import send_team_invitation
from .models import (
    Membership,
    Organization,
    OrganizationInvitation,
    PasswordResetDelivery,
    PilotApplication,
    User,
)
from .passwords import send_password_reset_delivery
from .throttles import LoginAccountRateThrottle


class FoundationApiTests(TestCase):
    def setUp(self):
        cache.clear()
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

    def test_mobile_token_login_issues_token_and_logout_revokes_it(self):
        response = self.client.post(
            "/api/v1/auth/token/",
            {"email": "ALICE@EXAMPLE.ORG", "password": "Alice-password-123"},
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

    def test_browser_login_requires_csrf_but_token_login_does_not(self):
        csrf_client = APIClient(enforce_csrf_checks=True)
        credentials = {
            "email": "alice@example.org",
            "password": "Alice-password-123",
        }
        rejected = csrf_client.post("/api/v1/auth/login/", credentials, format="json")
        self.assertEqual(rejected.status_code, 403)

        csrf_client.get("/api/v1/auth/csrf/")
        csrf_token = csrf_client.cookies["csrftoken"].value
        accepted = csrf_client.post(
            "/api/v1/auth/login/",
            credentials,
            format="json",
            HTTP_X_CSRFTOKEN=csrf_token,
        )
        self.assertEqual(accepted.status_code, 200, accepted.content)
        self.assertNotIn("token", accepted.json())

        token_client = APIClient(enforce_csrf_checks=True)
        token_response = token_client.post(
            "/api/v1/auth/token/", credentials, format="json"
        )
        self.assertEqual(token_response.status_code, 200, token_response.content)
        self.assertIn("token", token_response.json())

    @override_settings(
        REST_FRAMEWORK={
            **settings.REST_FRAMEWORK,
            "NUM_PROXIES": 0,
        }
    )
    def test_login_ip_ceiling_ignores_untrusted_forwarding_headers(self):
        cache.clear()
        account_rates = {
            **LoginAccountRateThrottle.THROTTLE_RATES,
            "auth_login_account": "100/minute",
        }
        scoped_rates = {
            **ScopedRateThrottle.THROTTLE_RATES,
            "auth_login_ip": "2/minute",
        }
        with (
            patch.object(LoginAccountRateThrottle, "THROTTLE_RATES", account_rates),
            patch.object(ScopedRateThrottle, "THROTTLE_RATES", scoped_rates),
        ):
            responses = [
                APIClient().post(
                    "/api/v1/auth/token/",
                    {"email": f"unknown-{index}@example.org", "password": "wrong"},
                    format="json",
                    REMOTE_ADDR="192.0.2.44",
                    HTTP_X_FORWARDED_FOR=f"203.0.113.{index + 10}",
                )
                for index in range(3)
            ]

        self.assertEqual(
            [response.status_code for response in responses], [400, 400, 429]
        )
        audit_request = APIRequestFactory().get(
            "/",
            REMOTE_ADDR="192.0.2.44",
            HTTP_X_FORWARDED_FOR="203.0.113.99",
        )
        event = AuditEvent.objects.record(action="proxy.test", request=audit_request)
        self.assertEqual(str(event.ip_address), "192.0.2.44")

    @override_settings(
        REST_FRAMEWORK={
            **settings.REST_FRAMEWORK,
            "NUM_PROXIES": 0,
        }
    )
    def test_login_account_ceiling_normalizes_email_across_addresses(self):
        cache.clear()
        account_rates = {
            **LoginAccountRateThrottle.THROTTLE_RATES,
            "auth_login_account": "2/minute",
        }
        scoped_rates = {
            **ScopedRateThrottle.THROTTLE_RATES,
            "auth_login_ip": "100/minute",
        }
        with (
            patch.object(LoginAccountRateThrottle, "THROTTLE_RATES", account_rates),
            patch.object(ScopedRateThrottle, "THROTTLE_RATES", scoped_rates),
        ):
            responses = [
                APIClient().post(
                    "/api/v1/auth/token/",
                    {
                        "email": email,
                        "password": "wrong",
                    },
                    format="json",
                    REMOTE_ADDR=f"192.0.2.{index + 10}",
                )
                for index, email in enumerate(
                    ["ALICE@EXAMPLE.ORG", "alice@example.org", " Alice@Example.org "]
                )
            ]

        self.assertEqual(
            [response.status_code for response in responses], [400, 400, 429]
        )

    @override_settings(PROJECT_HOPE_API_TOKEN_MAX_AGE_SECONDS=60)
    def test_native_api_tokens_expire_and_are_replaced_on_sign_in(self):
        expired = Token.objects.create(user=self.alice)
        Token.objects.filter(key=expired.key).update(
            created=timezone.now() - timedelta(minutes=2)
        )
        token_client = APIClient()
        token_client.credentials(HTTP_AUTHORIZATION=f"Token {expired.key}")
        self.assertEqual(token_client.get("/api/v1/me/").status_code, 401)
        self.assertFalse(Token.objects.filter(key=expired.key).exists())

        replacement = APIClient().post(
            "/api/v1/auth/token/",
            {"email": self.alice.email, "password": "Alice-password-123"},
            format="json",
        )
        self.assertEqual(replacement.status_code, 200, replacement.content)
        self.assertNotEqual(replacement.json()["token"], expired.key)

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

    def test_an_organization_must_retain_an_active_owner(self):
        self.login()

        demote = self.client.patch(
            f"/api/v1/organizations/alpha-charity/members/{self.alice_a.id}/",
            {"role": "staff"},
            format="json",
        )
        deactivate = self.client.patch(
            f"/api/v1/organizations/alpha-charity/members/{self.alice_a.id}/",
            {"active": False},
            format="json",
        )

        self.assertEqual(demote.status_code, 400)
        self.assertEqual(deactivate.status_code, 400)
        self.alice_a.refresh_from_db()
        self.assertEqual(self.alice_a.role, Membership.Role.OWNER)
        self.assertTrue(self.alice_a.active)

    def test_audit_events_are_append_only(self):
        event = AuditEvent.objects.record(action="test.event", actor=self.alice)

        event.action = "changed"
        with self.assertRaises(ValidationError):
            event.save()
        with self.assertRaises(ValidationError):
            event.delete()


@override_settings(
    EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
    PROJECT_HOPE_PUBLIC_URL="https://hope.example.org",
    PROJECT_HOPE_INVITATION_MAX_AGE_SECONDS=604800,
)
class OrganizationInvitationApiTests(TestCase):
    def setUp(self):
        cache.clear()
        self.client = APIClient()
        self.owner = User.objects.create_user("owner@example.org", "Owner-password-123")
        self.admin = User.objects.create_user("admin@example.org", "Admin-password-123")
        self.viewer = User.objects.create_user(
            "viewer@example.org", "Viewer-password-123"
        )
        self.existing = User.objects.create_user(
            "existing@example.org", "Existing-password-123"
        )
        self.organization = Organization.objects.create(
            name="North Star Centre", slug="north-star-centre"
        )
        Membership.objects.create(
            organization=self.organization,
            user=self.owner,
            role=Membership.Role.OWNER,
        )
        Membership.objects.create(
            organization=self.organization,
            user=self.admin,
            role=Membership.Role.ADMIN,
        )
        Membership.objects.create(
            organization=self.organization,
            user=self.viewer,
            role=Membership.Role.VIEWER,
        )

    def authenticate(self, user=None):
        self.client.force_authenticate(user=user or self.owner)

    def invite(self, email="new.person@example.org", role=Membership.Role.STAFF):
        self.authenticate()
        response = self.client.post(
            "/api/v1/organizations/north-star-centre/invitations/",
            {"email": email, "role": role},
            format="json",
        )
        self.assertEqual(response.status_code, 201, response.content)
        return response

    def token_from_latest_email(self):
        invitation_url = next(
            line
            for line in mail.outbox[-1].body.splitlines()
            if line.startswith("https://")
        )
        return parse_qs(urlparse(invitation_url).fragment)["invite_token"][0]

    def test_new_user_can_inspect_and_accept_a_single_use_invitation(self):
        response = self.invite(email=" New.Person@Example.org ")
        self.assertEqual(response.json()["email"], "new.person@example.org")
        self.assertEqual(response.json()["delivery_status"], "sent")
        self.assertEqual(len(mail.outbox), 1)
        token = self.token_from_latest_email()

        public_client = APIClient()
        preview = public_client.post(
            "/api/v1/invitations/inspect/", {"token": token}, format="json"
        )
        self.assertEqual(preview.status_code, 200, preview.content)
        self.assertEqual(preview.json()["organization"]["name"], "North Star Centre")
        self.assertEqual(preview.json()["roleLabel"], "Staff")
        self.assertFalse(preview.json()["existingAccount"])

        weak = public_client.post(
            "/api/v1/invitations/accept/",
            {
                "token": token,
                "password": "password",
                "password_confirm": "password",
            },
            format="json",
        )
        self.assertEqual(weak.status_code, 400)
        self.assertIn("password", weak.json())

        accepted = public_client.post(
            "/api/v1/invitations/accept/",
            {
                "token": token,
                "first_name": "Amina",
                "last_name": "Hope",
                "password": "Cedar-River-4827!",
                "password_confirm": "Cedar-River-4827!",
            },
            format="json",
        )
        self.assertEqual(accepted.status_code, 200, accepted.content)
        self.assertTrue(accepted.json()["signedIn"])
        self.assertTrue(accepted.json()["createdAccount"])
        user = User.objects.get(email="new.person@example.org")
        self.assertTrue(
            Membership.objects.filter(
                organization=self.organization,
                user=user,
                role=Membership.Role.STAFF,
                active=True,
            ).exists()
        )
        me = public_client.get("/api/v1/me/")
        self.assertEqual(me.status_code, 200, me.content)
        self.assertEqual(
            me.json()["organizations"][0]["organization"]["slug"], "north-star-centre"
        )

        reused = APIClient().post(
            "/api/v1/invitations/accept/",
            {
                "token": token,
                "password": "Different-Cedar-4827!",
                "password_confirm": "Different-Cedar-4827!",
            },
            format="json",
        )
        self.assertEqual(reused.status_code, 400)
        self.assertTrue(
            AuditEvent.objects.filter(
                organization=self.organization,
                action="invitation.accepted",
                actor=user,
            ).exists()
        )

    def test_existing_user_accepts_without_resetting_their_password(self):
        self.invite(email=self.existing.email, role=Membership.Role.COORDINATOR)
        token = self.token_from_latest_email()

        public_client = APIClient()
        accepted = public_client.post(
            "/api/v1/invitations/accept/", {"token": token}, format="json"
        )
        self.assertEqual(accepted.status_code, 200, accepted.content)
        self.assertFalse(accepted.json()["createdAccount"])
        self.assertFalse(accepted.json()["signedIn"])
        self.existing.refresh_from_db()
        self.assertTrue(self.existing.check_password("Existing-password-123"))
        self.assertTrue(
            Membership.objects.filter(
                organization=self.organization,
                user=self.existing,
                role=Membership.Role.COORDINATOR,
            ).exists()
        )

    def test_role_permissions_resend_and_revocation_invalidate_old_links(self):
        self.client.force_authenticate(user=self.viewer)
        forbidden_list = self.client.get(
            "/api/v1/organizations/north-star-centre/invitations/"
        )
        self.assertEqual(forbidden_list.status_code, 403)

        self.client.force_authenticate(user=self.admin)
        forbidden_owner = self.client.post(
            "/api/v1/organizations/north-star-centre/invitations/",
            {"email": "second-owner@example.org", "role": "owner"},
            format="json",
        )
        self.assertEqual(forbidden_owner.status_code, 403)

        invited = self.invite(email="resend@example.org")
        invitation_id = invited.json()["id"]
        old_token = self.token_from_latest_email()
        resent = self.client.post(
            f"/api/v1/organizations/north-star-centre/invitations/{invitation_id}/resend/",
            {},
            format="json",
        )
        self.assertEqual(resent.status_code, 200, resent.content)
        self.assertEqual(len(mail.outbox), 2)
        new_token = self.token_from_latest_email()
        self.assertNotEqual(old_token, new_token)
        self.assertEqual(
            APIClient()
            .post(
                "/api/v1/invitations/inspect/",
                {"token": old_token},
                format="json",
            )
            .status_code,
            400,
        )

        revoked = self.client.delete(
            f"/api/v1/organizations/north-star-centre/invitations/{invitation_id}/"
        )
        self.assertEqual(revoked.status_code, 204)
        self.assertEqual(
            APIClient()
            .post(
                "/api/v1/invitations/inspect/",
                {"token": new_token},
                format="json",
            )
            .status_code,
            400,
        )

    def test_expired_invitation_is_not_accepted(self):
        self.invite(email="expired@example.org")
        token = self.token_from_latest_email()
        OrganizationInvitation.objects.update(
            expires_at=timezone.now() - timedelta(seconds=1)
        )

        response = APIClient().post(
            "/api/v1/invitations/accept/",
            {
                "token": token,
                "password": "Cedar-River-4827!",
                "password_confirm": "Cedar-River-4827!",
            },
            format="json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertFalse(User.objects.filter(email="expired@example.org").exists())

    @patch("identity.invitations.logger.exception")
    @patch("identity.invitations.send_mail", side_effect=OSError("relay unavailable"))
    def test_failed_invitation_mail_is_recorded_and_retried(
        self, _failed_mail, logged_failure
    ):
        response = self.invite(email="retry@example.org")
        self.assertEqual(response.json()["delivery_status"], "retrying")
        invitation = OrganizationInvitation.objects.get(email="retry@example.org")
        logged_failure.assert_called_once()
        self.assertEqual(invitation.email_attempts, 1)
        self.assertIsNone(invitation.email_sent_at)
        with patch("identity.invitations.send_mail", return_value=1) as early_retry:
            self.assertFalse(send_team_invitation(invitation))
        early_retry.assert_not_called()
        invitation.refresh_from_db()
        self.assertEqual(invitation.email_attempts, 1)
        invitation.email_last_attempt_at = timezone.now() - timedelta(hours=1)
        invitation.save(update_fields=["email_last_attempt_at", "updated_at"])

        output = StringIO()
        with patch("identity.invitations.send_mail", return_value=1):
            management.call_command("retry_organization_invitations", stdout=output)
        invitation.refresh_from_db()
        self.assertIsNotNone(invitation.email_sent_at)
        self.assertEqual(invitation.email_attempts, 2)
        self.assertEqual(json.loads(output.getvalue())["delivered"], 1)


@override_settings(
    EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
    PROJECT_HOPE_PUBLIC_URL="https://hope.example.org",
    PASSWORD_RESET_TIMEOUT=3600,
)
class PasswordResetApiTests(TestCase):
    def setUp(self):
        cache.clear()
        self.user = User.objects.create_user(
            "amina@example.org", "Original-Cedar-4827!", first_name="Amina"
        )
        self.api_token = Token.objects.create(user=self.user)

    def reset_credentials(self):
        reset_url = next(
            line
            for line in mail.outbox[-1].body.splitlines()
            if line.startswith("https://")
        )
        return parse_qs(urlparse(reset_url).fragment)

    def test_request_is_non_enumerating_and_sends_only_for_active_account(self):
        known = APIClient().post(
            "/api/v1/auth/password-reset/",
            {"email": " AMINA@EXAMPLE.ORG "},
            format="json",
        )
        unknown = APIClient().post(
            "/api/v1/auth/password-reset/",
            {"email": "unknown@example.org"},
            format="json",
        )

        self.assertEqual(known.status_code, 202)
        self.assertEqual(unknown.status_code, 202)
        self.assertEqual(known.json(), unknown.json())
        self.assertEqual(len(mail.outbox), 0)
        delivery = PasswordResetDelivery.objects.get(user=self.user)
        self.assertEqual(delivery.status, PasswordResetDelivery.Status.PENDING)
        self.assertNotIn("reset", delivery.password_fingerprint)

        management.call_command("retry_password_reset_deliveries", verbosity=0)
        self.assertEqual(len(mail.outbox), 1)
        self.assertNotIn("amina@example.org", known.json()["detail"].lower())
        credentials = self.reset_credentials()
        self.assertIn("reset_uid", credentials)
        self.assertIn("reset_token", credentials)
        self.assertTrue(
            AuditEvent.objects.filter(
                actor=self.user, action="password.reset_queued"
            ).exists()
        )

    def test_valid_link_enforces_password_policy_and_is_single_use(self):
        client = APIClient()
        client.post(
            "/api/v1/auth/password-reset/",
            {"email": self.user.email},
            format="json",
        )
        management.call_command("retry_password_reset_deliveries", verbosity=0)
        credentials = self.reset_credentials()
        payload = {
            "uid": credentials["reset_uid"][0],
            "token": credentials["reset_token"][0],
        }
        preview = client.post(
            "/api/v1/auth/password-reset/inspect/", payload, format="json"
        )
        self.assertEqual(preview.status_code, 200, preview.content)
        self.assertEqual(preview.json()["email"], self.user.email)

        mismatch = client.post(
            "/api/v1/auth/password-reset/confirm/",
            {
                **payload,
                "password": "Cedar-River-9000!",
                "password_confirm": "different",
            },
            format="json",
        )
        self.assertEqual(mismatch.status_code, 400)
        weak = client.post(
            "/api/v1/auth/password-reset/confirm/",
            {**payload, "password": "password", "password_confirm": "password"},
            format="json",
        )
        self.assertEqual(weak.status_code, 400)
        changed = client.post(
            "/api/v1/auth/password-reset/confirm/",
            {
                **payload,
                "password": "Northern-Lights-9031!",
                "password_confirm": "Northern-Lights-9031!",
            },
            format="json",
        )
        self.assertEqual(changed.status_code, 200, changed.content)
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password("Northern-Lights-9031!"))
        self.assertFalse(Token.objects.filter(key=self.api_token.key).exists())
        self.assertEqual(
            client.post(
                "/api/v1/auth/password-reset/confirm/",
                {
                    **payload,
                    "password": "Another-Northern-9031!",
                    "password_confirm": "Another-Northern-9031!",
                },
                format="json",
            ).status_code,
            400,
        )
        self.assertTrue(
            AuditEvent.objects.filter(
                actor=self.user, action="password.reset_completed"
            ).exists()
        )

    def test_reset_delivery_retries_without_storing_the_reset_token(self):
        APIClient().post(
            "/api/v1/auth/password-reset/",
            {"email": self.user.email},
            format="json",
        )
        with (
            patch(
                "identity.passwords.send_mail",
                side_effect=OSError("relay unavailable"),
            ),
            patch("identity.passwords.logger.exception") as logged_failure,
        ):
            management.call_command("retry_password_reset_deliveries", verbosity=0)
        logged_failure.assert_called_once()
        delivery = PasswordResetDelivery.objects.get(user=self.user)
        self.assertEqual(delivery.status, PasswordResetDelivery.Status.PENDING)
        self.assertEqual(delivery.email_attempts, 1)
        with patch("identity.passwords.send_mail", return_value=1) as early_retry:
            self.assertFalse(send_password_reset_delivery(delivery))
        early_retry.assert_not_called()
        delivery.refresh_from_db()
        self.assertEqual(delivery.email_attempts, 1)
        delivery.email_last_attempt_at = timezone.now() - timedelta(hours=1)
        delivery.save(update_fields=["email_last_attempt_at", "updated_at"])

        with patch("identity.passwords.send_mail", return_value=1):
            management.call_command("retry_password_reset_deliveries", verbosity=0)
        delivery.refresh_from_db()
        self.assertEqual(delivery.status, PasswordResetDelivery.Status.SENT)
        self.assertEqual(delivery.email_attempts, 2)


@override_settings(
    EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
    PROJECT_HOPE_PUBLIC_URL="https://hope.example.org",
    PROJECT_HOPE_INVITATION_MAX_AGE_SECONDS=604800,
)
class BootstrapWorkspaceCommandTests(TestCase):
    def test_bootstrap_is_idempotent_and_sends_first_owner_invitation(self):
        output = StringIO()
        management.call_command(
            "bootstrap_workspace",
            organization="North Star Centre",
            owner_email="Owner@Example.org",
            stdout=output,
        )

        organization = Organization.objects.get(slug="north-star-centre")
        invitation = OrganizationInvitation.objects.get(organization=organization)
        self.assertEqual(invitation.email, "owner@example.org")
        self.assertEqual(invitation.role, Membership.Role.OWNER)
        self.assertEqual(invitation.status, OrganizationInvitation.Status.PENDING)
        self.assertIsNotNone(invitation.email_sent_at)
        self.assertEqual(json.loads(output.getvalue())["delivery"], "sent")
        self.assertNotIn("invite_token", output.getvalue())

        second_output = StringIO()
        management.call_command(
            "bootstrap_workspace",
            organization="North Star Centre",
            owner_email="owner@example.org",
            stdout=second_output,
        )
        self.assertEqual(Organization.objects.count(), 1)
        self.assertEqual(OrganizationInvitation.objects.count(), 1)
        invitation.refresh_from_db()
        self.assertEqual(invitation.token_version, 2)
        self.assertEqual(len(mail.outbox), 2)


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
