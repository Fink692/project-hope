# Requirements traceability matrix

| ID | Requirement | Design evidence | Current implementation/evidence | Status |
|---|---|---|---|---|
| R-01 | Self-hosted, local-first operation | Podman single-node topology; local Django auth; local PostgreSQL | `deploy/podman/compose.yml`, `services/core/project/settings.py` | Complete |
| R-02 | Authentication | Custom email user, password hashing, session login/logout | `identity.User`, `/api/v1/auth/login/`, auth tests | Complete |
| R-03 | Organizations and memberships | Organization + Membership models, owner assignment | `identity/models.py`, organization API | Complete |
| R-04 | Role-based authorization | Owner/admin/coordinator/staff/viewer role policy | `identity/permissions.py`, API authorization tests | Complete |
| R-05 | Tenant isolation | Organization membership is required before lookup; tenant FK is mandatory for audit events | organization and audit API tests | Complete |
| R-06 | Audit foundation | Append-only event model, manager, login/org/membership events | `audit.models.AuditEvent`, audit API tests | Complete |
| R-07 | Health checks | Unauthenticated liveness/readiness endpoint with database check | `/api/v1/healthz/`, health tests | Complete |
| R-08 | Seed data | Idempotent management command with environment-controlled password | `seed_demo` command | Complete |
| R-09 | Accessible web shell | Semantic landmarks, skip link, visible focus, status messaging, reduced motion | `apps/web/src/App.tsx`, `styles.css` | Complete |
| R-10 | AI disabled mode | Core UI and APIs do not depend on model services | no AI dependency in Phase 1 | Complete |
| R-11 | Replaceable AI gateway | Narrow deterministic operations, sidecar gateway, provenance and registry | `services/ai-gateway/main.py`, `services/core/modules/views.py`, gateway smoke tests | Complete |
| R-12 | Human approval before consequences | Workflow/email/translation/accessibility review gates and audit events | `services/core/modules/models.py`, `services/core/modules/views.py`, module tests | Complete |
| R-13 | Privacy/retention/deletion | Sensitivity fields, legal holds, preview/execute retention, tenant export and audit | `services/core/modules/management/commands`, `docs/privacy/data-handling.md` | Complete with operator restore/retention gates |
| R-14 | Threat model | STRIDE/AI-specific threats, mitigations, residual risk | `docs/threat-models/foundation.md`, `docs/full-build-status.md` | Complete with deployment residuals |
| R-15 | Automated verification | Backend/container tests, frontend/mobile checks, migration/check commands | `docs/full-build-status.md` | Complete |
