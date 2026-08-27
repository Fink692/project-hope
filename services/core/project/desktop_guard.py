"""Keep the local showcase inaccessible to websites and other network clients."""

import hmac
import json


class DesktopGuard:
    def __init__(self, application, *, token, origin):
        if len(token) < 40:
            raise ValueError("A random per-launch desktop token is required.")
        self.application = application
        self.token = token
        self.origin = origin
        self.host = origin.removeprefix("http://")

    def __call__(self, environ, start_response):
        token = environ.get("HTTP_X_PROJECT_HOPE_DESKTOP_TOKEN", "")
        origin = environ.get("HTTP_ORIGIN", "")
        if (
            environ.get("REMOTE_ADDR") != "127.0.0.1"
            or environ.get("HTTP_HOST") != self.host
            or (origin and origin != self.origin)
            or not hmac.compare_digest(
                token.encode("utf-8"), self.token.encode("utf-8")
            )
        ):
            return self.reject(start_response, "Open this workspace in Project Hope.")

        path = environ.get("PATH_INFO", "")
        writing = environ.get("REQUEST_METHOD") not in {"GET", "HEAD", "OPTIONS"}
        # A showcase must not accidentally send mail, collect applications,
        # contact a live telephone system, or change account security.
        external_write = any(
            value in path
            for value in (
                "/invitations/",
                "/pilot-applications/",
                "/auth/password-reset/",
                "/auth/mfa/",
                "/auth/token/",
                "/mailboxes/",
                "/developer/api-clients/",
                "/plugin-installations/",
            )
        ) or path.endswith(("/send/", "/action/", "/install/"))
        if path.startswith("/admin/") or (writing and external_write):
            return self.reject(
                start_response,
                "This action needs a connected charity workspace. "
                "The showcase uses sample data and cannot send external messages.",
            )

        def protected_response(status, headers, exc_info=None):
            headers.extend(
                [
                    ("Cache-Control", "no-store"),
                    ("X-Content-Type-Options", "nosniff"),
                    ("Referrer-Policy", "no-referrer"),
                    (
                        "Content-Security-Policy",
                        "default-src 'self'; script-src 'self'; "
                        "style-src 'self' 'unsafe-inline'; img-src 'self' data:; "
                        "connect-src 'self'; frame-ancestors 'none'; "
                        "object-src 'none'; base-uri 'self'; form-action 'self'",
                    ),
                ]
            )
            return start_response(status, headers, exc_info)

        return self.application(environ, protected_response)

    @staticmethod
    def reject(start_response, message):
        body = json.dumps({"detail": message}).encode()
        start_response(
            "403 Forbidden",
            [
                ("Content-Type", "application/json"),
                ("Content-Length", str(len(body))),
                ("Cache-Control", "no-store"),
            ],
        )
        return [body]
