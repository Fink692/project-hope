"""Isolated settings for the bundled, synthetic-data showcase workspace."""

import os
from pathlib import Path

from .settings import *  # noqa: F403


DEBUG = False
PROJECT_HOPE_DESKTOP_SHOWCASE = True
ALLOWED_HOSTS = ["127.0.0.1"]
ROOT_URLCONF = "project.desktop_urls"
SECURE_SSL_REDIRECT = False
SECURE_HSTS_SECONDS = 0
SECURE_HSTS_INCLUDE_SUBDOMAINS = False
SECURE_HSTS_PRELOAD = False
SESSION_COOKIE_SECURE = False
CSRF_COOKIE_SECURE = False
USE_X_FORWARDED_HOST = False
SECURE_PROXY_SSL_HEADER = None  # type: ignore[assignment]
PROJECT_HOPE_MFA_REQUIRED = False
EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": str(
            Path(os.environ["PROJECT_HOPE_DESKTOP_DATA_DIR"]) / "showcase.sqlite3"
        ),
        "OPTIONS": {"timeout": 30},
    }
}
MEDIA_ROOT = Path(os.environ["PROJECT_HOPE_DESKTOP_DATA_DIR"]) / "media"
CACHES = {"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}}
SESSION_COOKIE_NAME = "hope_showcase_session"
CSRF_COOKIE_NAME = "csrftoken"
SESSION_COOKIE_AGE = 12 * 60 * 60
