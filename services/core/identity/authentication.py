from datetime import timedelta

from django.conf import settings
from django.utils import timezone
from rest_framework.authentication import TokenAuthentication
from rest_framework.exceptions import AuthenticationFailed


def token_is_expired(token):
    return token.created <= timezone.now() - timedelta(
        seconds=settings.PROJECT_HOPE_API_TOKEN_MAX_AGE_SECONDS
    )


class ExpiringTokenAuthentication(TokenAuthentication):
    def authenticate_credentials(self, key):
        user, token = super().authenticate_credentials(key)
        if token_is_expired(token):
            token.delete()
            raise AuthenticationFailed("Token has expired. Sign in again.")
        return user, token
