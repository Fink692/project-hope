import base64
import binascii
import hashlib
import os
from pathlib import Path
from urllib.parse import parse_qsl, unquote, urlparse

from django.core.exceptions import ImproperlyConfigured


BASE_DIR = Path(__file__).resolve().parent.parent


def env_bool(name: str, default: bool = False) -> bool:
    value = os.environ.get(name)
    if value is None:
        return default
    return value.lower() in {"1", "true", "yes", "on"}


ENVIRONMENT = os.environ.get("DJANGO_ENV", "development").lower()
DEBUG = env_bool("DJANGO_DEBUG", ENVIRONMENT in {"development", "test"})
SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY", "")
if not SECRET_KEY:
    if ENVIRONMENT == "production":
        raise ImproperlyConfigured("DJANGO_SECRET_KEY is required in production.")
    SECRET_KEY = "development-only-change-me-before-sharing"
ALLOWED_HOSTS = [
    host.strip()
    for host in os.environ.get("DJANGO_ALLOWED_HOSTS", "localhost,127.0.0.1").split(",")
    if host.strip()
]

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "rest_framework",
    "rest_framework.authtoken",
    "audit",
    "identity",
    "modules",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "project.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "project.wsgi.application"
ASGI_APPLICATION = "project.asgi.application"

database_url = os.environ.get("DATABASE_URL", "")
if database_url.startswith(("postgres://", "postgresql://")):
    parsed_database = urlparse(database_url)
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": unquote(parsed_database.path.removeprefix("/")),
            "USER": unquote(parsed_database.username or "hope"),
            "PASSWORD": unquote(parsed_database.password or ""),
            "HOST": parsed_database.hostname or "localhost",
            "PORT": str(parsed_database.port or 5432),
            "OPTIONS": dict(parse_qsl(parsed_database.query, keep_blank_values=True)),
        }
    }
elif ENVIRONMENT == "production":
    raise ImproperlyConfigured("DATABASE_URL must be a PostgreSQL URL in production.")
else:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": os.environ.get(
                "PROJECT_HOPE_SQLITE_PATH", str(BASE_DIR / "db.sqlite3")
            ),
        }
    }

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"
    },
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
]

LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
MEDIA_URL = "media/"
MEDIA_ROOT = BASE_DIR / "media"
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
AUTH_USER_MODEL = "identity.User"

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "identity.authentication.ExpiringTokenAuthentication",
        "identity.authentication.SecurityVersionSessionAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "identity.permissions.IsAuthenticatedAndMfaCompliant",
    ],
    "DEFAULT_RENDERER_CLASSES": (
        [
            "rest_framework.renderers.JSONRenderer",
            "rest_framework.renderers.BrowsableAPIRenderer",
        ]
        if DEBUG
        else ["rest_framework.renderers.JSONRenderer"]
    ),
    "DEFAULT_THROTTLE_CLASSES": [
        "rest_framework.throttling.AnonRateThrottle",
        "rest_framework.throttling.UserRateThrottle",
    ],
    # Zero means direct connections use REMOTE_ADDR. Production Compose has one
    # trusted reverse proxy (Caddy); operators with another trusted proxy/CDN must
    # set the exact total instead of trusting arbitrary forwarded headers.
    "NUM_PROXIES": int(
        os.environ.get("DRF_NUM_PROXIES", "1" if ENVIRONMENT == "production" else "0")
    ),
    "DEFAULT_THROTTLE_RATES": {
        "anon": os.environ.get("DRF_ANON_RATE", "60/minute"),
        "user": os.environ.get("DRF_USER_RATE", "600/minute"),
        "pilot_application": os.environ.get("DRF_PILOT_APPLICATION_RATE", "10/hour"),
        "pilot_verification": os.environ.get("DRF_PILOT_VERIFICATION_RATE", "30/hour"),
        "invitation_public": os.environ.get("DRF_INVITATION_PUBLIC_RATE", "30/hour"),
        "password_reset_request": os.environ.get(
            "DRF_PASSWORD_RESET_REQUEST_RATE", "5/hour"
        ),
        "password_reset_token": os.environ.get(
            "DRF_PASSWORD_RESET_TOKEN_RATE", "30/hour"
        ),
        "auth_login_account": os.environ.get(
            "DRF_AUTH_LOGIN_ACCOUNT_RATE", "10/minute"
        ),
        "auth_login_ip": os.environ.get("DRF_AUTH_LOGIN_IP_RATE", "60/minute"),
        "auth_mfa_challenge": os.environ.get(
            "DRF_AUTH_MFA_CHALLENGE_RATE", "10/minute"
        ),
        "auth_mfa_enrollment": os.environ.get(
            "DRF_AUTH_MFA_ENROLLMENT_RATE", "10/hour"
        ),
    },
}

SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SECURE = not DEBUG
CSRF_COOKIE_SECURE = not DEBUG
CSRF_COOKIE_SAMESITE = "Lax"
SESSION_COOKIE_SAMESITE = "Lax"
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = "DENY"
SECURE_REFERRER_POLICY = "strict-origin-when-cross-origin"
SECURE_SSL_REDIRECT = env_bool("DJANGO_SECURE_SSL_REDIRECT", not DEBUG)
SECURE_HSTS_SECONDS = int(
    os.environ.get("DJANGO_HSTS_SECONDS", "0" if DEBUG else "31536000")
)
SECURE_HSTS_INCLUDE_SUBDOMAINS = env_bool("DJANGO_HSTS_INCLUDE_SUBDOMAINS", not DEBUG)
SECURE_HSTS_PRELOAD = env_bool("DJANGO_HSTS_PRELOAD", not DEBUG)
USE_X_FORWARDED_HOST = env_bool("DJANGO_USE_X_FORWARDED_HOST", False)
if env_bool("DJANGO_TRUST_PROXY", not DEBUG):
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

csrf_origins = os.environ.get("DJANGO_CSRF_TRUSTED_ORIGINS", "")
CSRF_TRUSTED_ORIGINS = [
    origin.strip() for origin in csrf_origins.split(",") if origin.strip()
]
DATA_UPLOAD_MAX_MEMORY_SIZE = int(
    os.environ.get("DJANGO_DATA_UPLOAD_MAX_MEMORY_SIZE", str(10 * 1024 * 1024))
)
FILE_UPLOAD_MAX_MEMORY_SIZE = int(
    os.environ.get("DJANGO_FILE_UPLOAD_MAX_MEMORY_SIZE", str(10 * 1024 * 1024))
)
PROJECT_HOPE_MAX_DOCUMENT_BYTES = int(
    os.environ.get("PROJECT_HOPE_MAX_DOCUMENT_BYTES", str(25 * 1024 * 1024))
)
PROJECT_HOPE_MAX_UNCOMPRESSED_DOCUMENT_BYTES = int(
    os.environ.get(
        "PROJECT_HOPE_MAX_UNCOMPRESSED_DOCUMENT_BYTES", str(100 * 1024 * 1024)
    )
)
PROJECT_HOPE_MAX_DOCUMENT_ARCHIVE_MEMBERS = int(
    os.environ.get("PROJECT_HOPE_MAX_DOCUMENT_ARCHIVE_MEMBERS", "1000")
)
PROJECT_HOPE_MAX_CRM_IMPORT_BYTES = int(
    os.environ.get("PROJECT_HOPE_MAX_CRM_IMPORT_BYTES", str(5 * 1024 * 1024))
)
PROJECT_HOPE_MAX_CRM_IMPORT_ROWS = int(
    os.environ.get("PROJECT_HOPE_MAX_CRM_IMPORT_ROWS", "2500")
)
PROJECT_HOPE_CRM_IMPORT_PREVIEW_MAX_AGE_SECONDS = int(
    os.environ.get("PROJECT_HOPE_CRM_IMPORT_PREVIEW_MAX_AGE_SECONDS", "900")
)

EMAIL_BACKEND = os.environ.get(
    "EMAIL_BACKEND", "django.core.mail.backends.smtp.EmailBackend"
)
EMAIL_HOST = os.environ.get("SMTP_HOST", "localhost")
EMAIL_PORT = int(os.environ.get("SMTP_PORT", "25"))
EMAIL_USE_TLS = env_bool("SMTP_STARTTLS", False)
EMAIL_USE_SSL = env_bool("SMTP_USE_SSL", False)
EMAIL_HOST_USER = os.environ.get("SMTP_USERNAME", "")
EMAIL_HOST_PASSWORD = os.environ.get("SMTP_PASSWORD", "")
EMAIL_TIMEOUT = int(os.environ.get("SMTP_TIMEOUT_SECONDS", "10"))
DEFAULT_FROM_EMAIL = os.environ.get("SMTP_FROM", "Project Hope <noreply@example.org>")
PROJECT_HOPE_PUBLIC_URL = os.environ.get("PROJECT_HOPE_PUBLIC_URL", "").rstrip("/")
if not PROJECT_HOPE_PUBLIC_URL and ENVIRONMENT != "production":
    PROJECT_HOPE_PUBLIC_URL = "http://localhost:5173"
if EMAIL_USE_TLS and EMAIL_USE_SSL:
    raise ImproperlyConfigured("Enable only one of SMTP_STARTTLS or SMTP_USE_SSL.")
if ENVIRONMENT == "production":
    public_url = urlparse(PROJECT_HOPE_PUBLIC_URL)
    if (
        public_url.scheme != "https"
        or not public_url.netloc
        or public_url.username
        or public_url.password
        or public_url.query
        or public_url.fragment
    ):
        raise ImproperlyConfigured(
            "PROJECT_HOPE_PUBLIC_URL must be a credential-free HTTPS origin or path "
            "without a query or fragment in production."
        )
    if not os.environ.get("SMTP_HOST") or not os.environ.get("SMTP_FROM"):
        raise ImproperlyConfigured(
            "SMTP_HOST and SMTP_FROM are required in production."
        )
PROJECT_HOPE_PILOT_VERIFICATION_MAX_AGE_SECONDS = int(
    os.environ.get("PROJECT_HOPE_PILOT_VERIFICATION_MAX_AGE_SECONDS", "604800")
)
PROJECT_HOPE_PILOT_EMAIL_RETRY_SECONDS = int(
    os.environ.get("PROJECT_HOPE_PILOT_EMAIL_RETRY_SECONDS", "900")
)
PROJECT_HOPE_PILOT_EMAIL_RETRY_BATCH_SIZE = int(
    os.environ.get("PROJECT_HOPE_PILOT_EMAIL_RETRY_BATCH_SIZE", "20")
)
PROJECT_HOPE_INVITATION_MAX_AGE_SECONDS = int(
    os.environ.get("PROJECT_HOPE_INVITATION_MAX_AGE_SECONDS", "604800")
)
PROJECT_HOPE_INVITATION_EMAIL_RETRY_SECONDS = int(
    os.environ.get("PROJECT_HOPE_INVITATION_EMAIL_RETRY_SECONDS", "900")
)
PROJECT_HOPE_INVITATION_EMAIL_RETRY_BATCH_SIZE = int(
    os.environ.get("PROJECT_HOPE_INVITATION_EMAIL_RETRY_BATCH_SIZE", "20")
)
PASSWORD_RESET_TIMEOUT = int(os.environ.get("PASSWORD_RESET_TIMEOUT", "3600"))
PROJECT_HOPE_API_TOKEN_MAX_AGE_SECONDS = int(
    os.environ.get("PROJECT_HOPE_API_TOKEN_MAX_AGE_SECONDS", "2592000")
)
PROJECT_HOPE_MFA_REQUIRED = env_bool(
    "PROJECT_HOPE_MFA_REQUIRED", ENVIRONMENT == "production"
)
PROJECT_HOPE_MFA_ISSUER = os.environ.get(
    "PROJECT_HOPE_MFA_ISSUER", "Project Hope"
).strip()
PROJECT_HOPE_MFA_LOGIN_CHALLENGE_MAX_AGE_SECONDS = int(
    os.environ.get("PROJECT_HOPE_MFA_LOGIN_CHALLENGE_MAX_AGE_SECONDS", "300")
)
PROJECT_HOPE_MFA_ENROLLMENT_MAX_AGE_SECONDS = int(
    os.environ.get("PROJECT_HOPE_MFA_ENROLLMENT_MAX_AGE_SECONDS", "600")
)
PROJECT_HOPE_MFA_TOTP_VALID_WINDOW = int(
    os.environ.get("PROJECT_HOPE_MFA_TOTP_VALID_WINDOW", "1")
)
PROJECT_HOPE_MFA_RECOVERY_CODE_COUNT = int(
    os.environ.get("PROJECT_HOPE_MFA_RECOVERY_CODE_COUNT", "10")
)
mfa_encryption_keys = os.environ.get("PROJECT_HOPE_MFA_ENCRYPTION_KEYS", "").strip()
if not mfa_encryption_keys:
    if ENVIRONMENT == "production":
        raise ImproperlyConfigured(
            "PROJECT_HOPE_MFA_ENCRYPTION_KEYS is required in production."
        )
    mfa_encryption_keys = base64.urlsafe_b64encode(
        hashlib.sha256(f"project-hope-mfa:{SECRET_KEY}".encode()).digest()
    ).decode()
PROJECT_HOPE_MFA_ENCRYPTION_KEYS = tuple(
    key.strip() for key in mfa_encryption_keys.split(",") if key.strip()
)
for mfa_encryption_key in PROJECT_HOPE_MFA_ENCRYPTION_KEYS:
    try:
        decoded_mfa_key = base64.b64decode(
            mfa_encryption_key.encode(), altchars=b"-_", validate=True
        )
    except (ValueError, binascii.Error) as exc:
        raise ImproperlyConfigured(
            "Every PROJECT_HOPE_MFA_ENCRYPTION_KEYS value must be a Fernet key."
        ) from exc
    if len(decoded_mfa_key) != 32:
        raise ImproperlyConfigured(
            "Every PROJECT_HOPE_MFA_ENCRYPTION_KEYS value must decode to 32 bytes."
        )
if not PROJECT_HOPE_MFA_ISSUER:
    raise ImproperlyConfigured("PROJECT_HOPE_MFA_ISSUER cannot be empty.")
if PROJECT_HOPE_MFA_TOTP_VALID_WINDOW not in {0, 1}:
    raise ImproperlyConfigured("PROJECT_HOPE_MFA_TOTP_VALID_WINDOW must be 0 or 1.")
if not 8 <= PROJECT_HOPE_MFA_RECOVERY_CODE_COUNT <= 20:
    raise ImproperlyConfigured(
        "PROJECT_HOPE_MFA_RECOVERY_CODE_COUNT must be between 8 and 20."
    )
PROJECT_HOPE_PASSWORD_RESET_QUEUE_MAX_AGE_SECONDS = int(
    os.environ.get("PROJECT_HOPE_PASSWORD_RESET_QUEUE_MAX_AGE_SECONDS", "900")
)
PROJECT_HOPE_PASSWORD_RESET_EMAIL_RETRY_SECONDS = int(
    os.environ.get("PROJECT_HOPE_PASSWORD_RESET_EMAIL_RETRY_SECONDS", "120")
)
PROJECT_HOPE_PASSWORD_RESET_EMAIL_RETRY_BATCH_SIZE = int(
    os.environ.get("PROJECT_HOPE_PASSWORD_RESET_EMAIL_RETRY_BATCH_SIZE", "20")
)
PROJECT_HOPE_PASSWORD_RESET_DELIVERY_RETENTION_DAYS = int(
    os.environ.get("PROJECT_HOPE_PASSWORD_RESET_DELIVERY_RETENTION_DAYS", "7")
)
PROJECT_HOPE_PILOT_UNVERIFIED_RETENTION_DAYS = int(
    os.environ.get("PROJECT_HOPE_PILOT_UNVERIFIED_RETENTION_DAYS", "14")
)
PROJECT_HOPE_PILOT_DECLINED_RETENTION_DAYS = int(
    os.environ.get("PROJECT_HOPE_PILOT_DECLINED_RETENTION_DAYS", "90")
)
PROJECT_HOPE_PILOT_INACTIVE_RETENTION_DAYS = int(
    os.environ.get("PROJECT_HOPE_PILOT_INACTIVE_RETENTION_DAYS", "365")
)

valkey_url = os.environ.get("VALKEY_URL", "")
if ENVIRONMENT == "production" and not valkey_url:
    raise ImproperlyConfigured(
        "VALKEY_URL is required in production for shared throttles and one-time "
        "authentication challenges."
    )
if valkey_url:
    CACHES = {
        "default": {
            "BACKEND": "django.core.cache.backends.redis.RedisCache",
            "LOCATION": valkey_url,
        }
    }
else:
    CACHES = {"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}}
