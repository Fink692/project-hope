# Project Hope full-build status

Date: 2026-07-31

The complete roadmap is implemented as a release-hardened, self-hosted product baseline in the repository. Domain records are organization-scoped, the web/mobile clients use the same API boundary, and consequential actions remain reviewable or deterministic.

| Roadmap area | Implementation | Verification |
|---|---|---|
| Identity, organizations, RBAC, tenant isolation | Django identity app and scoped APIs | Authorization matrix tests |
| Audit and privacy foundation | Append-only events, retention policies, export command | Audit and command checks |
| CRM | Contacts, households, relationships, interactions, consent | Tenant/API tests |
| Volunteers | Applications, pipeline review, profiles, skills, availability | Acceptance/review test |
| Scheduling | Programs, events, shifts, waitlist, iCalendar export | Calendar test |
| Documents | Secure model, uploaded-file metadata, extraction, passages, search | Extraction/search test |
| AI gateway/workflows | Local bounded gateway, schema-shaped outputs, risk flags, review states | Workflow and gateway smoke tests |
| Email assistant | Mailbox/message records, IMAP minimization, drafting, approval, SMTP send | Mailpit/container test |
| Analytics | Metric definitions, snapshots, summaries | Metrics test |
| Grants | Workspaces, questions, evidence workflow, deterministic budget validation | Budget test |
| Community resources | Search, language/accessibility filtering, freshness, verification, scoped public API | Public API test |
| Translation | Local glossary fallback, jobs, memory, human review | Translation test |
| Accessibility | Transformation records, plain-language adapter, human approval, accessible web/mobile UI | Frontend/mobile type checks |
| PWA/offline | Manifest, service worker, offline shell, bounded local draft storage, and protected cache exclusions | Web build/test |
| Voice | Consent/call records, bounded intent, safety flags, transfer/callback controls | Voice safety test |
| Donor insights | Descriptive rule-based snapshots/cohorts with opt-out/reason codes | Cohort test |
| Plugin catalogue | Manifest/permission validation, admin install/revoke, capability tokens, disabled-by-default execution boundary | Plugin governance test |
| Public API | Scoped client issuance, one-time secret, explicit scopes, rate limit, public resources endpoint | Client/API test |
| Native mobile | Expo client with token authentication, secure storage, live tenant-scoped records, expiring safe snapshots, offline note, accessibility states, release configuration, and fail-closed production API URL handling | Frozen install, TypeScript check, Expo config, web export, and Expo doctor |
| Charity onboarding | Guided Windows/macOS/Linux setup helper, friendly lifecycle commands, plain-language operator guide, and in-app first-run path | Helper doctor/setup smoke, web tests/build, live health/root smoke |
| App distribution | Installable standalone web app, hosted-workspace distribution guide, and Expo iPhone/Android release configuration | PWA manifest/build, mobile Expo config/export, Expo Doctor, web tests/build |
| Desktop installers | Native Windows, macOS, and Linux installers with hosted-workspace preconfiguration, first-run connection screen, and update channel | Desktop TypeScript build, electron-builder targets, GitHub Actions matrix with clean-runner build step |
| Operations | Docker/Podman stack, worker, model registry, backups, retention/export commands, Django admin, reverse-proxy routing, production static volume | Dev and production Compose validation, startup smoke tests, static/admin route checks |

## Required external runtimes

The software paths are implemented without paid dependencies. A charity may add local Tika/OCRmyPDF/Tesseract, Docling, Whisper/faster-whisper, Kokoro, Asterisk/SIP, Keycloak/OIDC federation, and a real local LLM by configuring the documented sidecar boundaries. The deterministic adapter remains the safe fallback when those runtimes are absent; it never claims semantic model quality or performs side effects.

## Verification run

- Local Django suite: 24 tests passed.
- Containerized Django suite against PostgreSQL/pgvector: 24 tests passed.
- Ruff lint/format: passed.
- Mypy: passed.
- Migration drift check: passed.
- Web Vitest: passed.
- Web TypeScript/Vite build: passed.
- Mobile TypeScript check: passed.
- Docker Compose build: passed.
- Docker Compose startup: passed; reverse-proxy health and AI gateway health confirmed.
- Production Compose topology: passed; Gunicorn health, collected static assets, Caddy routing, and worker ordering validated with synthetic configuration.
- AI gateway boundary: passed; configured internal calls use the bounded sidecar with authenticated optional token and deterministic fallback.
- Upload safety: passed; document size and MIME limits are enforced before persistence.
- Legal hold safety: passed; direct deletes are blocked for held record types and retention execution is audited.
- Admin boundary: passed; retention policies and AI model registry are not readable by viewer-role members.
- Django admin route: passed; `/admin/` is proxied to the authenticated operational UI.
