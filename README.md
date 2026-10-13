# Project Hope

A charity operations workspace for contacts, volunteers, programs, schedules, documents, and grants.

[Website and downloads](https://project-hope-charities.vercel.app) · [Install guide](https://project-hope-charities.vercel.app/guide) · [Build status](docs/full-build-status.md)

## Try the desktop preview

The desktop app opens a fictional sample workspace without an account, server address, or database setup. Sample edits persist on the device. A shared charity account requires a separately hosted workspace.

The latest published desktop release is [v1.9.2](https://github.com/Fink692/project-hope/releases/tag/v1.9.2). Installers are unsigned. The website provides Windows, Apple-silicon macOS, and Linux downloads. Native mobile clients are in the repository; App Store and Google Play releases are not established here.

Generative assistance uses compatible local models. When unavailable, the app labels its limited templates. Core operations remain usable with AI disabled.

## Product

| Area | Capabilities |
| --- | --- |
| Contacts | Reviewed CSV/XLSX migration, duplicate handling, relationships, consent, and portable export |
| Coordination | Volunteers, programs, events, shifts, waitlists, and calendars |
| Research | Document extraction, search, grants, and evidence workflows |
| Assistance | Local AI adapters, draft review, translation, and bounded communications workflows |
| Access | Organization scope, roles, expiring invitations, two-step verification, recovery, and audit history |

[Contact import screenshots and guide](docs/MOVING_CONTACTS_FOR_CHARITIES.md) · [Charity walkthrough](docs/DISTRIBUTION_FOR_CHARITIES.md)

## Architecture

| Path | Responsibility |
| --- | --- |
| `services/core/` | Django domain API and workers |
| `apps/web/` | React web app and PWA |
| `apps/desktop/` | Electron shell and bundled sample runtime |
| `apps/mobile/` | Mobile client |
| `deploy/podman/` | Compose services and reverse proxy |
| `docs/` | Architecture, operations, and release records |

Data ownership, organization scope, and human review are part of the application design. Production configuration requires appropriate secrets, encryption keys, backups, monitoring, and a synthetic-data staging check.

## Local training workspace

Requires Docker Desktop or Podman Desktop.

Windows:

```powershell
.\scripts\project-hope.ps1 setup
```

macOS/Linux:

```sh
bash scripts/project-hope.sh setup
```

The helper starts the local services, opens the browser, and shows the demo sign-in. [Training setup](docs/GETTING_STARTED_FOR_CHARITIES.md).

## Developer workspace

The repository is organized as a modular monolith with replaceable clients:

| Area | Location |
|---|---|
| Domain API and workers | `services/core` |
| Web app and PWA shell | `apps/web` |
| Native mobile client | `apps/mobile` |
| Native desktop installers | `apps/desktop` |
| Compose and reverse proxy | `deploy/podman` |
| Architecture, operations, and decisions | `docs` |

### Web development

```powershell
cd apps/web
pnpm install
pnpm dev
```

The web shell runs at `http://127.0.0.1:5173/` and proxies `/api` to Django.

### API development

```powershell
cd services/core
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements-dev.txt
$env:DJANGO_SETTINGS_MODULE = "project.settings"
python manage.py migrate
python manage.py seed_demo
python manage.py runserver
```

### Verification

```powershell
cd services/core
python manage.py check
python manage.py test
ruff check project audit identity
mypy .

cd ..\..\apps\web
pnpm test
pnpm build

cd ..\desktop
pnpm install --frozen-lockfile
pnpm run build
```

GitHub Actions also verifies the backend, web client, mobile client, desktop packaging matrix, onboarding helpers, Compose files, and production configuration.

## Hosting and pilot operations

Shared team use needs a hosted workspace, HTTPS, account setup, email delivery, security configuration, and verified backups. These are separate from installing the sample app.

[Production deployment](docs/operations/production-deployment.md) · [Desktop packaging](apps/desktop/README.md) · [Pilot runbook](docs/commercial-readiness.md) · [Pilot privacy notice](docs/privacy/pilot-applications.md)

The source is publicly visible, but the repository does not include an approved software license. Public visibility does not grant reuse rights.
