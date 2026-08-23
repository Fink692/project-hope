import hashlib

from rest_framework.throttling import SimpleRateThrottle


class LoginAccountRateThrottle(SimpleRateThrottle):
    """Limit credential attempts per normalized account without caching the email."""

    scope = "auth_login_account"

    def get_cache_key(self, request, view):
        email = str(request.data.get("email", "")).strip().lower()
        identifier = email or self.get_ident(request)
        digest = hashlib.sha256(identifier.encode("utf-8")).hexdigest()
        return self.cache_format % {"scope": self.scope, "ident": digest}


class MfaChallengeRateThrottle(SimpleRateThrottle):
    """Limit attempts per signed login challenge without caching the credential."""

    scope = "auth_mfa_challenge"

    def get_cache_key(self, request, view):
        challenge = str(request.data.get("challenge", "")).strip()
        identifier = challenge or self.get_ident(request)
        digest = hashlib.sha256(identifier.encode("utf-8")).hexdigest()
        return self.cache_format % {"scope": self.scope, "ident": digest}
