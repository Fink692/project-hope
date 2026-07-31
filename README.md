# Project Hope

**A calm, controlled operating system for community impact.**

[![Quality gate](https://github.com/Fink692/project-hope/actions/workflows/ci.yml/badge.svg)](https://github.com/Fink692/project-hope/actions/workflows/ci.yml)
[![Release](https://img.shields.io/github/v/release/Fink692/project-hope?display_name=tag&color=1f7a5a)](https://github.com/Fink692/project-hope/releases)
[![Architecture](https://img.shields.io/badge/dependencies-self--hosted%20%26%20local--first-235347)](docs/full-build-status.md)

Project Hope is a self-hosted, local-first operations platform for charities. It brings identity, CRM, volunteers, scheduling, documents, bounded AI, email, analytics, grants, resources, translation, accessibility, PWA/offline workflows, voice safety controls, donor insights, plugins, a public API, and native mobile field workflows into one auditable workspace.

The product is designed around a simple promise: **charities keep control of their data, people stay in the loop, and useful operations continue even when AI is disabled.**

## Why it stands out

| Built for trust | Built for momentum |
|---|---|
| Organization-scoped access, RBAC, audit history, legal holds, data minimization, and safe upload handling | One workspace for frontline work, volunteers, grants, resources, communications, scheduling, and impact operations |
| Deterministic AI fallback, bounded gateway, explicit review states, and no unrestricted autonomous agents | Self-hosted PostgreSQL/pgvector, Valkey, Keycloak, Mailpit, Caddy, and optional local model runtimes |
| Accessible web/mobile surfaces, keyboard-first workflows, reduced-motion support, and fail-closed production configuration | React + TypeScript web PWA, Expo mobile client, Django API, worker, public API, and production Compose topology |

## Product surface

- **Coordinate:** contacts, households, relationships, consent, volunteers, programs, events, shifts, waitlists, and iCalendar export.
- **Understand:** secure documents, bounded extraction, search, analytics, grants, evidence workflows, resources, translation, and donor insights.
- **Communicate safely:** minimized mailbox imports, injection flags, draft approval, SMTP delivery, voice consent, callbacks, and transfer controls.
- **Extend responsibly:** governed plugin catalogue, scoped public API clients, capability tokens, append-only audit events, and explicit human review.

The repository follows the research recommendation of a modular monolith first:

- `services/core`: Django + Django REST Framework domain and API foundation
- `apps/web`: React + TypeScript + Vite workspace and PWA shell
- `apps/mobile`: Expo/React Native authenticated field-workflow client
- `deploy/podman`: local single-node services and reverse proxy configuration
- `docs`: requirements, architecture, threat model, operations, and decisions

The platform remains useful with AI disabled. Any AI-like operation uses bounded deterministic adapters or a replaceable local gateway, with review state and audit coverage for consequential outputs.

> **Release status:** Project Hope 1.0 is a release-hardened, self-hosted product baseline. See the [full build status](docs/full-build-status.md) for the verification record and the [production deployment guide](docs/operations/production-deployment.md) for operator-owned launch gates.

## Quick start

### Local Python development

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

The API is available at `http://127.0.0.1:8000/api/v1/healthz/`.

### Web development

```powershell
cd apps/web
pnpm install
pnpm dev
```

The web shell is available at `http://127.0.0.1:5173/` and proxies `/api` to Django.

### Podman single-node development environment

```powershell
podman compose -f deploy/podman/compose.yml up --build
```

This starts PostgreSQL with pgvector, Valkey, Keycloak, Mailpit, Django, the production-built web shell, the bounded AI gateway, and Caddy. See [local development](docs/operations/local-development.md) for environment variables, seeded credentials, and troubleshooting.

## Verification

```powershell
cd services/core
python manage.py check
python manage.py test
ruff check project audit identity
mypy .

cd ..\..\apps\web
pnpm build
pnpm test
```

The original foundation acceptance criteria are in [docs/phase-1-acceptance.md](docs/phase-1-acceptance.md). The complete roadmap is implemented as a release-hardened product baseline; module-specific verification and external-runtime notes are in [docs/full-build-status.md](docs/full-build-status.md).

The complete roadmap status is documented in [docs/full-build-status.md](docs/full-build-status.md), including the public API contract, worker commands, PWA/mobile surfaces, and optional local model/telephony runtimes.

## Project principles

- Charity-controlled data and replaceable local infrastructure
- Human approval before consequential actions
- Explicit tenant and programme scope on every future domain record
- Least privilege, append-only audit history, and data minimization
- Accessible interfaces and keyboard-first workflows
- No paid API or cloud service is a required dependency
- No unrestricted autonomous agents
