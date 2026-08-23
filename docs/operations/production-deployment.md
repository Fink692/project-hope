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
- `AI_GATEWAY_TOKEN`
- `DRF_NUM_PROXIES` when the request path contains more than the bundled Caddy proxy (the Compose default is `1`; count only trusted reverse proxies)

Use a private network, encrypted disks, a firewall that exposes only 80/443, and an encrypted restic repository. Do not use the development compose file or the demo seed credentials for real data.

Production startup fails closed unless `DATABASE_URL` uses PostgreSQL. Percent-encoded credentials and PostgreSQL connection query options such as an operator-required TLS mode are preserved. `PROJECT_HOPE_SQLITE_PATH` exists only for isolated development and automated preview databases; it is ignored as a production substitute.

Do not increase `DRF_NUM_PROXIES` speculatively. Its value must equal the number of trusted proxies closest to Project Hope. An incorrect value can make rate limits group unrelated users or trust a caller-supplied forwarding address.

## Start and verify

```powershell
docker compose --env-file .env.production -f deploy/podman/compose.production.yml config -q
docker compose --env-file .env.production -f deploy/podman/compose.production.yml up -d --build
docker compose --env-file .env.production -f deploy/podman/compose.production.yml ps
```

Verify the public health endpoint, sign-in flow, admin redirect, Caddy certificate, worker logs, outbound email, and a synthetic document upload before importing real records. If the Founding 10 form is enabled, submit and confirm one synthetic application, inspect `python manage.py pilot_metrics`, remove the synthetic record, and verify the application-retention worker. Run `deploy/systemd/backup.ps1` or `backup.sh`, then perform a restore drill into separate staging targets.

## Create the first workspace owner

After HTTPS and SMTP delivery are verified, create the organization and send its first owner a private account-setup link:

```powershell
docker compose --env-file .env.production -f deploy/podman/compose.production.yml exec core python manage.py bootstrap_workspace --organization "North Star Centre" --owner-email "owner@northstar.example"
```

The command is idempotent, never prints the invitation credential, and reports `sent` or `retrying`. The background worker retries mail that the SMTP relay did not accept. The owner opens the expiring one-time link, chooses a password, enters the workspace, and can then use **Team & access** to invite everyone else. Run the command only from a trusted operator terminal; do not place personal email addresses in checked-in environment files or shell history shared with others.

## Identity and data gates

The repository currently ships the tested local password/session boundary, expiring team invitations, and organization-scoped authorization. Keycloak is present in the development topology as an integration boundary, but OIDC token validation and MFA enrollment are not implemented in the application yet. Do not describe the current build as MFA-enabled. Before beneficiary or other high-sensitivity production data is loaded, either complete and independently test that integration or place the deployment behind an organization-approved access gateway that enforces MFA, short privileged sessions, and recovery procedures. Remove or rotate all demo credentials.

Retention is explicit and audited. Review policies and legal holds with the organization before enabling `run_retention --execute`; direct API deletion is blocked while the matching record type is under legal hold.

## Founding 10 operator gate

The public application is ready in the product but must not be advertised until transactional email, a monitored privacy/support contact, service-provider disclosures, and the public origin have been verified. Follow [commercial readiness and Founding 10 runbook](../commercial-readiness.md). Application confirmation links expire after seven days by default, public submissions are throttled, and stale application records are removed by the background worker under the documented retention schedule.
