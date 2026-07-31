# Phase 1 results (historical checkpoint)

Date: 2026-07-31

This document records the foundation checkpoint. The later roadmap modules are no longer deferred; see [full-build-status.md](full-build-status.md) for the current complete-build status.

## Completed

- Empty repository converted into a documented modular-monolith foundation.
- Django/DRF backend with a custom email user, password hashing, session login/logout, current-user endpoint, organization creation/list/detail, memberships, owner/admin/coordinator/staff/viewer roles, and scoped authorization.
- Tenant isolation tests that hide organizations and audit events from users without active membership.
- Append-only audit events for authentication, organization, membership, and audit access.
- Public health/readiness endpoint with a database probe.
- Idempotent development seed command.
- React/TypeScript/Vite web shell with keyboard-visible focus, skip link, semantic landmarks, status region, responsive layout, and reduced-motion support.
- Podman Compose topology for PostgreSQL/pgvector, Valkey, Keycloak, Mailpit, Django, Vite, and Caddy.
- Requirements summary, traceability matrix, architecture, agent-flow design, threat model, data model, API plan, repository structure, ADRs, roadmap, privacy baseline, setup guide, and acceptance criteria.

## Verification evidence

| Check | Result |
|---|---|
| `python manage.py check` | Passed |
| `python manage.py makemigrations --check --dry-run` | Passed; no changes detected |
| Django tests | 10 passed |
| Ruff lint | Passed |
| Ruff format check | Passed |
| Mypy (`--ignore-missing-imports`) | Passed |
| Frontend Vitest | 1 test passed |
| Frontend TypeScript/Vite production build | Passed |
| Frozen pnpm install | Passed |

## Deferred at the Phase 1 checkpoint

CRM, volunteer management, scheduling, document ingestion/search, Keycloak token federation, Celery/Valkey workers, AI gateway, email drafting, analytics, grants, resource search, translation, PWA/offline, voice, donor insights, plugins, native mobile, production backups, and formal accessibility/manual security review.

## Security limitations

The default local environment uses a development Django secret, development database credentials, a demo account password, Keycloak development credentials, and HTTP. It is not suitable for real personal information. Production requires secret rotation, HTTPS, Keycloak/OIDC with MFA, secure cookies, trusted hosts, encrypted disks/backups, restricted database access, rate limiting, monitoring, backup restore tests, and a documented incident process.

The audit model prevents application-level `save()` and `delete()` changes, but database administrators can still change data. Stronger tamper evidence or immutable storage is a later hardening option.

## Recommended next milestone

Build the CRM core: contacts, households, organizations, relationships, consent, communication preferences, programme participation, interactions, configurable tags, safe import/export, duplicate review, sensitivity labels, retention hooks, and audit coverage. It is the first domain module that validates the foundation without requiring AI.
