# Local development

## Supported baseline

- Windows, Linux, or macOS for development
- Python 3.12+
- Node.js 20+ and pnpm 9+
- PostgreSQL 16 with pgvector for the container path
- Podman Compose or Docker Compose for the full local stack

SQLite is used when `DATABASE_URL` is absent so the foundation test suite can run without a database daemon. Use PostgreSQL for integration testing and any realistic data volume.

## Python setup

```powershell
cd services/core
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements-dev.txt
python manage.py migrate
python manage.py seed_demo
python manage.py runserver
```

The seeded development account is `demo@example.org`. Its password is read from `DEMO_ADMIN_PASSWORD` and defaults to `change-me-now` only for local development. Change it immediately for any shared environment.

## Web setup

```powershell
cd apps/web
pnpm install
pnpm dev
```

Vite proxies `/api` to `http://127.0.0.1:8000`.

## Full Podman setup

```powershell
podman compose -f deploy/podman/compose.yml up --build
```

Open `http://localhost:8090` (or set `HOPE_HTTP_PORT`). Django admin is at `/admin/`, Keycloak is on `http://localhost:8081`, and Mailpit is on `http://localhost:8025`. The compose file is a development topology, not a production hardening profile.

## Production cautions

Do not load real charity data into the default development stack. Production requires HTTPS, secure cookies, a strong secret, trusted host configuration, Keycloak/MFA, encrypted disks and backups, restricted database exposure, secret rotation, monitoring, backup restore tests, and a documented incident process.

## Background workers and privacy operations

The full local topology includes a worker service. It runs:

```powershell
python manage.py poll_mailboxes
python manage.py process_documents
python manage.py run_retention --organization hope-demo
python manage.py export_organization hope-demo .\hope-demo-export.json
```

Retention is preview-only unless `--execute` is supplied. Legal holds disable a policy. Mailbox passwords are referenced through environment variable names stored in `credential_ref`; raw credentials and complete mailbox bodies are never put in source control.

For production, use `deploy/systemd/backup.sh` or `backup.ps1` with PostgreSQL custom dumps and restic-encrypted media backups. A backup job is not considered successful until a restore is tested.

Run deploy/systemd/restore-drill.sh or restore-drill.ps1 only against explicitly separate staging database and filesystem targets. Both scripts require an explicit confirmation and never infer a production target.

For a hardened host deployment, use [production deployment](production-deployment.md) with `deploy/podman/compose.production.yml`. It replaces Django’s development server with Gunicorn and uses Caddy-managed HTTPS.

## Common checks

```powershell
cd services/core
python manage.py check
python manage.py test
python manage.py showmigrations
ruff check .
mypy .

cd ..\..\apps\web
pnpm build
pnpm test

cd ..\mobile
pnpm install --frozen-lockfile
pnpm exec tsc --noEmit
```
