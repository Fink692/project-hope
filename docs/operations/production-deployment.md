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

Use a private network, encrypted disks, a firewall that exposes only 80/443, and an encrypted restic repository. Do not use the development compose file or the demo seed credentials for real data.

## Start and verify

```powershell
docker compose --env-file .env.production -f deploy/podman/compose.production.yml config -q
docker compose --env-file .env.production -f deploy/podman/compose.production.yml up -d --build
docker compose --env-file .env.production -f deploy/podman/compose.production.yml ps
```

Verify the public health endpoint, sign-in flow, admin redirect, Caddy certificate, worker logs, outbound email, and a synthetic document upload before importing real records. If the Founding 10 form is enabled, submit and confirm one synthetic application, inspect `python manage.py pilot_metrics`, remove the synthetic record, and verify the application-retention worker. Run `deploy/systemd/backup.ps1` or `backup.sh`, then perform a restore drill into separate staging targets.

## Identity and data gates

The repository ships a local password boundary for development and automated tests. Before production data is loaded, connect the organization’s Keycloak/OIDC provider with MFA, short privileged sessions, recovery procedures, and demo-account removal or rotation. The application authorization policy remains organization-scoped independently of the identity provider.

Retention is explicit and audited. Review policies and legal holds with the organization before enabling `run_retention --execute`; direct API deletion is blocked while the matching record type is under legal hold.

## Founding 10 operator gate

The public application is ready in the product but must not be advertised until transactional email, a monitored privacy/support contact, service-provider disclosures, and the public origin have been verified. Follow [commercial readiness and Founding 10 runbook](../commercial-readiness.md). Application confirmation links expire after seven days by default, public submissions are throttled, and stale application records are removed by the background worker under the documented retention schedule.
