from datetime import timedelta

from django.conf import settings
from django.contrib.auth import logout
from django.utils import timezone
from rest_framework.authentication import SessionAuthentication, TokenAuthentication
from rest_framework.exceptions import AuthenticationFailed

from .mfa import SESSION_MFA_CREDENTIAL_KEY, SESSION_SECURITY_VERSION_KEY
from .models import MultiFactorCredential


def token_is_expired(token):
    return (
        token.created < token.user.security_changed_at
        or token.created
        <= timezone.now()
        - timedelta(seconds=settings.PROJECT_HOPE_API_TOKEN_MAX_AGE_SECONDS)
    )


class ExpiringTokenAuthentication(TokenAuthentication):
    def authenticate_credentials(self, key):
        user, token = super().authenticate_credentials(key)
        if token_is_expired(token):
            token.delete()
            raise AuthenticationFailed("Token has expired. Sign in again.")
        return user, token


class SecurityVersionSessionAuthentication(SessionAuthentication):
    """Reject sessions superseded by a password or MFA security change."""

    def authenticate(self, request):
        authenticated = super().authenticate(request)
        if authenticated is None:
            return None
        user, auth = authenticated
        session_version = request.session.get(SESSION_SECURITY_VERSION_KEY)
        if session_version is None and user.security_version == 0:
            request.session[SESSION_SECURITY_VERSION_KEY] = 0
            session_version = 0
        if session_version != user.security_version:
            logout(request._request)
            raise AuthenticationFailed("Session expired. Sign in again.")
        try:
            credential = user.mfa_credential
        except MultiFactorCredential.DoesNotExist:
            credential = None
        if credential is not None and request.session.get(
            SESSION_MFA_CREDENTIAL_KEY
        ) != str(credential.id):
            logout(request._request)
            raise AuthenticationFailed("Two-step verification is required.")
        return user, auth
