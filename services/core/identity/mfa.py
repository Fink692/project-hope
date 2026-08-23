import base64
import hashlib
import hmac
import io
import re
import secrets
import time
from dataclasses import dataclass

import pyotp
import qrcode
import qrcode.image.svg
from cryptography.fernet import Fernet, InvalidToken, MultiFernet
from django.conf import settings
from django.core.cache import cache
from django.core import signing
from django.db import transaction
from rest_framework.authtoken.models import Token

from .models import MultiFactorCredential, User


MFA_LOGIN_SALT = "project-hope.mfa-login.v1"
MFA_ENROLLMENT_SALT = "project-hope.mfa-enrollment.v1"
SESSION_SECURITY_VERSION_KEY = "hope_security_version"
SESSION_MFA_CREDENTIAL_KEY = "hope_mfa_credential"
TOTP_PATTERN = re.compile(r"^[0-9]{6}$")
RECOVERY_PATTERN = re.compile(r"^[A-Z2-9]{10}$")
RECOVERY_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"


class InvalidMfaChallenge(Exception):
    pass


class InvalidMfaEnrollment(Exception):
    pass


class InvalidMfaCode(Exception):
    pass


class MfaAlreadyEnabled(Exception):
    pass


class MfaNotEnabled(Exception):
    pass


class MfaSecretUnavailable(Exception):
    pass


@dataclass(frozen=True)
class VerifiedMfaCode:
    credential: MultiFactorCredential
    method: str


def _fernet() -> MultiFernet:
    return MultiFernet(
        [Fernet(key.encode()) for key in settings.PROJECT_HOPE_MFA_ENCRYPTION_KEYS]
    )


def encrypt_secret(secret: str) -> str:
    return _fernet().encrypt(secret.encode()).decode()


def decrypt_secret(encrypted_secret: str) -> str:
    try:
        return _fernet().decrypt(encrypted_secret.encode()).decode()
    except (InvalidToken, UnicodeDecodeError) as exc:
        raise MfaSecretUnavailable from exc


def password_fingerprint(user: User) -> str:
    return hashlib.sha256(user.password.encode()).hexdigest()


def _recovery_digest_for_key(code: str, encoded_key: str) -> str:
    key = base64.urlsafe_b64decode(encoded_key.encode())
    digest_key = hashlib.sha256(key + b":project-hope-recovery-v1").digest()
    return hmac.new(digest_key, code.encode(), hashlib.sha256).hexdigest()


def encryption_key_id(encoded_key: str) -> str:
    key = base64.urlsafe_b64decode(encoded_key.encode())
    return hashlib.sha256(key).hexdigest()[:16]


def current_encryption_key_id() -> str:
    return encryption_key_id(settings.PROJECT_HOPE_MFA_ENCRYPTION_KEYS[0])


def _recovery_digest(code: str) -> str:
    return _recovery_digest_for_key(code, settings.PROJECT_HOPE_MFA_ENCRYPTION_KEYS[0])


def _candidate_recovery_digests(code: str) -> list[str]:
    return [
        _recovery_digest_for_key(code, key)
        for key in settings.PROJECT_HOPE_MFA_ENCRYPTION_KEYS
    ]


def normalize_recovery_code(code: str) -> str:
    return "".join(character for character in code.upper() if character.isalnum())


def generate_recovery_codes() -> tuple[list[str], list[str], str]:
    codes: list[str] = []
    digests: list[str] = []
    while len(codes) < settings.PROJECT_HOPE_MFA_RECOVERY_CODE_COUNT:
        compact = "".join(secrets.choice(RECOVERY_ALPHABET) for _ in range(10))
        code = f"{compact[:5]}-{compact[5:]}"
        digest = _recovery_digest(compact)
        if digest in digests:
            continue
        codes.append(code)
        digests.append(digest)
    return codes, digests, current_encryption_key_id()


def rotate_encrypted_secret(encrypted_secret: str) -> str:
    try:
        return _fernet().rotate(encrypted_secret.encode()).decode()
    except (InvalidToken, UnicodeDecodeError) as exc:
        raise MfaSecretUnavailable from exc


def _totp_counter(secret: str, code: str, last_used_counter: int) -> int | None:
    normalized = code.strip()
    if not TOTP_PATTERN.fullmatch(normalized):
        return None
    totp = pyotp.TOTP(secret)
    current_counter = int(time.time()) // totp.interval
    window = settings.PROJECT_HOPE_MFA_TOTP_VALID_WINDOW
    for offset in (0, -1, 1):
        if abs(offset) > window:
            continue
        counter = current_counter + offset
        if counter <= last_used_counter:
            continue
        expected = totp.at(counter * totp.interval)
        if hmac.compare_digest(expected, normalized):
            return counter
    return None


def _locked_credential(user: User) -> MultiFactorCredential:
    try:
        return MultiFactorCredential.objects.select_for_update().get(user=user)
    except MultiFactorCredential.DoesNotExist as exc:
        raise MfaNotEnabled from exc


def _consume_locked_code(
    credential: MultiFactorCredential, raw_code: str
) -> VerifiedMfaCode:
    normalized_totp = raw_code.strip()
    if TOTP_PATTERN.fullmatch(normalized_totp):
        counter = _totp_counter(
            decrypt_secret(credential.encrypted_secret),
            normalized_totp,
            credential.last_used_counter,
        )
        if counter is None:
            raise InvalidMfaCode
        credential.last_used_counter = counter
        credential.save(update_fields=["last_used_counter", "updated_at"])
        return VerifiedMfaCode(credential=credential, method="totp")

    recovery_code = normalize_recovery_code(raw_code)
    if not RECOVERY_PATTERN.fullmatch(recovery_code):
        raise InvalidMfaCode
    candidates = _candidate_recovery_digests(recovery_code)
    matched_index = next(
        (
            index
            for index, digest in enumerate(credential.recovery_code_hashes)
            if any(
                hmac.compare_digest(str(digest), candidate) for candidate in candidates
            )
        ),
        None,
    )
    if matched_index is None:
        raise InvalidMfaCode
    credential.recovery_code_hashes = [
        digest
        for index, digest in enumerate(credential.recovery_code_hashes)
        if index != matched_index
    ]
    credential.save(update_fields=["recovery_code_hashes", "updated_at"])
    return VerifiedMfaCode(credential=credential, method="recovery_code")


@transaction.atomic
def consume_mfa_code(user: User, raw_code: str) -> VerifiedMfaCode:
    return _consume_locked_code(_locked_credential(user), raw_code)


def issue_login_challenge(user: User, mode: str) -> str:
    if mode not in {"session", "token"}:
        raise ValueError("Unsupported MFA login mode.")
    return signing.dumps(
        {
            "uid": str(user.id),
            "mode": mode,
            "nonce": secrets.token_urlsafe(24),
            "password": password_fingerprint(user),
            "security": user.security_version,
        },
        salt=MFA_LOGIN_SALT,
        compress=True,
    )


def user_from_login_challenge(token: str) -> tuple[User, str]:
    try:
        payload = signing.loads(
            token,
            salt=MFA_LOGIN_SALT,
            max_age=settings.PROJECT_HOPE_MFA_LOGIN_CHALLENGE_MAX_AGE_SECONDS,
        )
        user = User.objects.get(id=payload["uid"], is_active=True)
    except (
        signing.BadSignature,
        signing.SignatureExpired,
        KeyError,
        TypeError,
        ValueError,
        User.DoesNotExist,
    ) as exc:
        raise InvalidMfaChallenge from exc
    mode = payload.get("mode")
    if (
        mode not in {"session", "token"}
        or not isinstance(payload.get("nonce"), str)
        or len(payload["nonce"]) < 24
        or payload.get("password") != password_fingerprint(user)
        or payload.get("security") != user.security_version
        or not MultiFactorCredential.objects.filter(user=user).exists()
    ):
        raise InvalidMfaChallenge
    return user, mode


def reserve_login_challenge(token: str) -> str:
    """Atomically reserve a challenge so one password proof can sign in once."""

    digest = hashlib.sha256(token.encode()).hexdigest()
    key = f"hope:mfa-login-used:{digest}"
    if not cache.add(
        key,
        "reserved",
        timeout=settings.PROJECT_HOPE_MFA_LOGIN_CHALLENGE_MAX_AGE_SECONDS,
    ):
        raise InvalidMfaChallenge
    return key


def release_login_challenge(reservation_key: str) -> None:
    """Allow another attempt when verification failed before authentication."""

    cache.delete(reservation_key)


def _qr_code_data_url(uri: str) -> str:
    image = qrcode.make(uri, image_factory=qrcode.image.svg.SvgPathImage, border=3)
    output = io.BytesIO()
    image.save(output)
    encoded = base64.b64encode(output.getvalue()).decode()
    return f"data:image/svg+xml;base64,{encoded}"


def begin_enrollment(user: User) -> dict:
    if MultiFactorCredential.objects.filter(user=user).exists():
        raise MfaAlreadyEnabled
    secret = pyotp.random_base32(length=32)
    uri = pyotp.TOTP(secret).provisioning_uri(
        name=user.email, issuer_name=settings.PROJECT_HOPE_MFA_ISSUER
    )
    token = signing.dumps(
        {
            "uid": str(user.id),
            "secret": secret,
            "password": password_fingerprint(user),
            "security": user.security_version,
        },
        salt=MFA_ENROLLMENT_SALT,
        compress=True,
    )
    return {
        "enrollmentToken": token,
        "secret": secret,
        "formattedSecret": " ".join(
            secret[index : index + 4] for index in range(0, len(secret), 4)
        ),
        "otpauthUri": uri,
        "qrCodeDataUrl": _qr_code_data_url(uri),
        "expiresInSeconds": settings.PROJECT_HOPE_MFA_ENROLLMENT_MAX_AGE_SECONDS,
    }


def _secret_from_enrollment(user: User, enrollment_token: str) -> str:
    try:
        payload = signing.loads(
            enrollment_token,
            salt=MFA_ENROLLMENT_SALT,
            max_age=settings.PROJECT_HOPE_MFA_ENROLLMENT_MAX_AGE_SECONDS,
        )
        secret = str(payload["secret"])
    except (
        signing.BadSignature,
        signing.SignatureExpired,
        KeyError,
        TypeError,
        ValueError,
    ) as exc:
        raise InvalidMfaEnrollment from exc
    if (
        payload.get("uid") != str(user.id)
        or payload.get("password") != password_fingerprint(user)
        or payload.get("security") != user.security_version
        or not re.fullmatch(r"[A-Z2-7]{32}", secret)
    ):
        raise InvalidMfaEnrollment
    return secret


@transaction.atomic
def confirm_enrollment(
    user: User, enrollment_token: str, code: str
) -> tuple[MultiFactorCredential, list[str]]:
    locked_user = User.objects.select_for_update().get(id=user.id)
    if MultiFactorCredential.objects.filter(user=locked_user).exists():
        raise MfaAlreadyEnabled
    secret = _secret_from_enrollment(locked_user, enrollment_token)
    counter = _totp_counter(secret, code, -1)
    if counter is None:
        raise InvalidMfaCode
    recovery_codes, recovery_hashes, recovery_key_id = generate_recovery_codes()
    credential = MultiFactorCredential.objects.create(
        user=locked_user,
        encrypted_secret=encrypt_secret(secret),
        recovery_code_hashes=recovery_hashes,
        recovery_key_id=recovery_key_id,
        last_used_counter=counter,
    )
    locked_user.security_version += 1
    locked_user.save(update_fields=["security_version"])
    Token.objects.filter(user=locked_user).delete()
    user.security_version = locked_user.security_version
    return credential, recovery_codes


@transaction.atomic
def regenerate_recovery_codes(
    user: User, code: str
) -> tuple[MultiFactorCredential, list[str], str]:
    locked_user = User.objects.select_for_update().get(id=user.id)
    verified = _consume_locked_code(_locked_credential(locked_user), code)
    recovery_codes, recovery_hashes, recovery_key_id = generate_recovery_codes()
    verified.credential.recovery_code_hashes = recovery_hashes
    verified.credential.recovery_key_id = recovery_key_id
    verified.credential.save(
        update_fields=["recovery_code_hashes", "recovery_key_id", "updated_at"]
    )
    locked_user.security_version += 1
    locked_user.save(update_fields=["security_version"])
    Token.objects.filter(user=locked_user).delete()
    user.security_version = locked_user.security_version
    return verified.credential, recovery_codes, verified.method


@transaction.atomic
def disable_mfa(user: User, code: str) -> str:
    locked_user = User.objects.select_for_update().get(id=user.id)
    verified = _consume_locked_code(_locked_credential(locked_user), code)
    verified.credential.delete()
    locked_user.security_version += 1
    locked_user.save(update_fields=["security_version"])
    Token.objects.filter(user=locked_user).delete()
    user.security_version = locked_user.security_version
    return verified.method


@transaction.atomic
def reset_mfa_by_operator(user: User) -> MultiFactorCredential:
    locked_user = User.objects.select_for_update().get(id=user.id)
    credential = _locked_credential(locked_user)
    credential.delete()
    locked_user.security_version += 1
    locked_user.save(update_fields=["security_version"])
    Token.objects.filter(user=locked_user).delete()
    user.security_version = locked_user.security_version
    return credential


def mfa_status(user: User) -> dict:
    credential = MultiFactorCredential.objects.filter(user=user).first()
    enabled = credential is not None
    required = bool(settings.PROJECT_HOPE_MFA_REQUIRED)
    return {
        "enabled": enabled,
        "required": required,
        "enrollmentRequired": required and not enabled,
        "enabledAt": credential.enabled_at if credential else None,
        "recoveryCodesRemaining": (
            len(credential.recovery_code_hashes) if credential else 0
        ),
    }


def set_session_security(request, user: User, *, mfa_verified: bool) -> None:
    request.session[SESSION_SECURITY_VERSION_KEY] = user.security_version
    credential = MultiFactorCredential.objects.filter(user=user).first()
    if credential is None:
        request.session.pop(SESSION_MFA_CREDENTIAL_KEY, None)
    elif mfa_verified:
        request.session[SESSION_MFA_CREDENTIAL_KEY] = str(credential.id)
    else:
        request.session.pop(SESSION_MFA_CREDENTIAL_KEY, None)
