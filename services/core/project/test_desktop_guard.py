import json

from django.test import SimpleTestCase

from .desktop_guard import DesktopGuard


class DesktopGuardTests(SimpleTestCase):
    def setUp(self):
        self.token = "test-only-launch-token-" * 4
        self.environ = {
            "REMOTE_ADDR": "127.0.0.1",
            "HTTP_HOST": "127.0.0.1:43210",
            "HTTP_X_PROJECT_HOPE_DESKTOP_TOKEN": self.token,
            "PATH_INFO": "/api/v1/healthz/",
            "REQUEST_METHOD": "GET",
        }
        self.guard = DesktopGuard(
            lambda environ, start: self.application(start),
            token=self.token,
            origin="http://127.0.0.1:43210",
        )

    def application(self, start):
        start("200 OK", [("Content-Type", "application/json")])
        return [b"{}"]

    def call(self, **changes):
        response = {}

        def start(status, headers, exc_info=None):
            response.update(status=status, headers=dict(headers))

        response["body"] = json.loads(
            b"".join(self.guard({**self.environ, **changes}, start))
        )
        return response

    def test_only_a_per_launch_authenticated_request_is_allowed(self):
        self.assertEqual(self.call()["status"], "200 OK")
        self.assertEqual(
            self.call(HTTP_X_PROJECT_HOPE_DESKTOP_TOKEN="")["status"],
            "403 Forbidden",
        )

    def test_other_hosts_network_clients_and_website_origins_are_rejected(self):
        for changes in [
            {"HTTP_HOST": "attacker.example:43210"},
            {"HTTP_HOST": "127.0.0.1:43211"},
            {"REMOTE_ADDR": "192.168.1.5"},
            {"HTTP_ORIGIN": "https://attacker.example"},
            {"HTTP_ORIGIN": "null"},
        ]:
            with self.subTest(changes=changes):
                self.assertEqual(self.call(**changes)["status"], "403 Forbidden")

    def test_no_external_side_effects_can_be_triggered_in_the_sample(self):
        for path in [
            "/api/v1/organizations/hope-showcase/email-drafts/id/send/",
            "/api/v1/organizations/hope-showcase/invitations/",
            "/api/v1/organizations/hope-showcase/calls/id/action/",
            "/api/v1/organizations/hope-showcase/plugins/id/install/",
            "/api/v1/auth/mfa/enrollment/",
            "/api/v1/pilot-applications/",
        ]:
            with self.subTest(path=path):
                self.assertEqual(
                    self.call(PATH_INFO=path, REQUEST_METHOD="POST")["status"],
                    "403 Forbidden",
                )

    def test_ordinary_sample_edits_are_allowed(self):
        self.assertEqual(
            self.call(
                PATH_INFO="/api/v1/organizations/hope-showcase/contacts/",
                REQUEST_METHOD="POST",
            )["status"],
            "200 OK",
        )

    def test_security_headers_and_no_store_are_applied(self):
        headers = self.call()["headers"]
        self.assertEqual(headers["Cache-Control"], "no-store")
        self.assertIn("frame-ancestors 'none'", headers["Content-Security-Policy"])

    def test_weak_launch_tokens_are_rejected(self):
        with self.assertRaises(ValueError):
            DesktopGuard(None, token="guessable", origin="http://127.0.0.1:43210")
