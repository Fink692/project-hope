# Production deployment

The production topology is in `deploy/podman/compose.production.yml`. It runs Django under Gunicorn, serves the built web bundle from Nginx, publishes collected Django static assets through a shared read-only Caddy volume, keeps PostgreSQL/Valkey/AI internal, persists Caddy certificates, and enables HTTPS through Caddy.

## Required operator values

Create an operator-owned environment file outside the repository and set:

- `HOPE_DOMAIN`
- `DJANGO_SECRET_KEY` (a new high-entropy value)
- `DJANGO_ALLOWED_HOSTS` and `DJANGO_CSRF_TRUSTED_ORIGINS`
- `DATABASE_URL` for the production PostgreSQL instance
- `POSTGRES_PASSWORD` when the bundled database is used
- `SMTP_HOST`, `SMTP_FROM`, and the SMTP transport settings
- `SMTP_USERNAME` and `SMTP_PASSWORD` when the relay requires authentication
- `PROJECT_HOPE_PUBLIC_URL` (the exact HTTPS origin used in confirmation links)
- `PROJECT_HOPE_MFA_ENCRYPTION_KEYS` (a dedicated Fernet key; never reuse `DJANGO_SECRET_KEY`)
- `AI_GATEWAY_TOKEN`
- `DRF_NUM_PROXIES` when the request path contains more than the bundled Caddy proxy (the Compose default is `1`; count only trusted reverse proxies)

Use a private network, encrypted disks, a firewall that exposes only 80/443, and an encrypted restic repository. Do not use the development compose file or the demo seed credentials for real data.

Generate the first MFA encryption key on an operator-controlled computer and place only the output in the private production environment file:

```powershell
py -3 -c "import base64,secrets; print(base64.urlsafe_b64encode(secrets.token_bytes(32)).decode())"
```

On macOS or Linux, use `python3` in place of `py -3`. Keep the environment file outside the repository, restrict its filesystem permissions, include it in the operator's secrets backup, and never paste a real key into an issue, chat, screenshot, or support log. Custom production topologies must also set `VALKEY_URL` to a shared Valkey/Redis instance; the supplied Compose topology does this automatically. Production startup fails closed when either the MFA key or shared cache is missing.

Production startup fails closed unless `DATABASE_URL` uses PostgreSQL. Percent-encoded credentials and PostgreSQL connection query options such as an operator-required TLS mode are preserved. `PROJECT_HOPE_SQLITE_PATH` exists only for isolated development and automated preview databases; it is ignored as a production substitute.

Do not increase `DRF_NUM_PROXIES` speculatively. Its value must equal the number of trusted proxies closest to Project Hope. An incorrect value can make rate limits group unrelated users or trust a caller-supplied forwarding address.

## Start and verify

```powershell
docker compose --env-file .env.production -f deploy/podman/compose.production.yml config -q
docker compose --env-file .env.production -f deploy/podman/compose.production.yml up -d --build
docker compose --env-file .env.production -f deploy/podman/compose.production.yml ps
```

Verify the public health endpoint, first-time two-step enrollment, a fresh-browser MFA sign-in, one recovery-code sign-in, admin redirect, Caddy certificate, worker logs, outbound email, and a synthetic document upload before importing real records. Confirm that organization names and records remain unavailable before required enrollment. If the Founding 10 form is enabled, submit and confirm one synthetic application, inspect `python manage.py pilot_metrics`, remove the synthetic record, and verify the application-retention worker. Run `deploy/systemd/backup.ps1` or `backup.sh`, then perform a restore drill into separate staging targets.

## Create the first workspace owner

After HTTPS and SMTP delivery are verified, create the organization and send its first owner a private account-setup link:

```powershell
docker compose --env-file .env.production -f deploy/podman/compose.production.yml exec core python manage.py bootstrap_workspace --organization "North Star Centre" --owner-email "owner@northstar.example"
```

The command is idempotent, never prints the invitation credential, and reports `sent` or `retrying`. The background worker retries mail that the SMTP relay did not accept. The owner opens the expiring one-time link, chooses a password, enrolls a standards-based authenticator app, saves the one-time recovery codes, and can then use **Team & access** to invite everyone else. Run the command only from a trusted operator terminal; do not place personal email addresses in checked-in environment files or shell history shared with others.

## Identity and data gates

Project Hope ships built-in TOTP two-step verification for browser and native sign-in. Production requires enrollment before organization metadata or records can open. Authenticator secrets are encrypted at rest, recovery codes are stored only as keyed hashes and work once, accepted TOTP time steps cannot be replayed, password challenges are short-lived and single-use, and password/MFA changes supersede older sessions and native tokens. OIDC federation remains available as a future SSO integration, not a prerequisite for the built-in control.

Before beneficiary or other high-sensitivity production data is loaded, complete a clean-device test with the real domain and SMTP path, independently review authorization and session settings, define privileged-session and access-review policy, and remove or rotate every demo credential. Built-in MFA reduces account-takeover risk; it does not replace phishing-resistant hardware credentials, endpoint security, operator access controls, or incident response.

## MFA recovery and key rotation

A user with an unavailable authenticator signs in with one saved recovery code, then creates a replacement set from **Account security**. Creating a new set invalidates every previous recovery code. If the user has neither an authenticator nor a recovery code, an authorized operator must complete the charity's identity-recovery procedure and run:

```powershell
docker compose --env-file .env.production -f deploy/podman/compose.production.yml exec core python manage.py reset_user_mfa --email "person@example.org" --confirm-email "person@example.org" --reason "Approved support case PH-123"
```

The command requires exact email confirmation, records the reason, revokes sessions/tokens, removes only that user's MFA credential, and sends a security notification after the reset commits. Never reset MFA from an unverified email request alone.

For encryption-key rotation, prepend a new key to `PROJECT_HOPE_MFA_ENCRYPTION_KEYS`, retain the prior keys after it, restart the core and worker, then validate and execute re-encryption:

```powershell
docker compose --env-file .env.production -f deploy/podman/compose.production.yml exec core python manage.py rotate_mfa_encryption
docker compose --env-file .env.production -f deploy/podman/compose.production.yml exec core python manage.py rotate_mfa_encryption --execute
```

The dry run validates every encrypted secret without writing. The execute pass re-encrypts TOTP secrets with the first key and audits each credential. Recovery codes cannot be re-keyed without revealing them, so keep prior keys configured while the command reports legacy recovery-code sets. Those users must regenerate their codes—or complete an approved MFA reset—before the old key is removed. Back up the new key before rotation and test sign-in plus recovery in staging first.

Retention is explicit and audited. Review policies and legal holds with the organization before enabling `run_retention --execute`; direct API deletion is blocked while the matching record type is under legal hold.

## Founding 10 operator gate

The public application is ready in the product but must not be advertised until transactional email, a monitored privacy/support contact, service-provider disclosures, and the public origin have been verified. Follow [commercial readiness and Founding 10 runbook](../commercial-readiness.md). Application confirmation links expire after seven days by default, public submissions are throttled, and stale application records are removed by the background worker under the documented retention schedule.
