# Project Hope product-readiness evidence

Date: 2026-08-23

Project Hope is a broad, installable product baseline—not a field-validated finished charity platform. This document separates code that exists from integrations, human validation, and commercial operations that still require proof. A model, endpoint, or automated test is not presented as evidence that a real charity workflow has passed acceptance testing.

## Status language

- **Implemented:** the path exists in the repository and has automated coverage.
- **Baseline:** useful domain/API behavior exists, but the full workflow or specialist interface is not yet proven.
- **Integration required:** organization-owned infrastructure, credentials, or policy must be connected and tested.
- **External validation required:** acceptance depends on charity users, accessibility participants, bilingual reviewers, safety specialists, or independent review.
- **Not implemented:** the original specification names a capability that this repository does not yet supply.

## Current evidence by product area

| Product area | What is implemented now | What remains before a production claim |
|---|---|---|
| Identity, organizations, RBAC, tenant isolation | Case-normalized email users, Django password hashing, sessions, expiring native tokens, non-enumerating one-time password recovery, organizations, five membership roles, scoped lookups, append-only access events | OIDC/MFA application integration, privileged-session policy, independent authorization testing |
| Team onboarding | Expiring single-use signed invitations, first-account password setup, existing-account acceptance, owner/admin role rules, resend/revoke, mail retry, bootstrap command, in-app Team & access UI | Production SMTP validation and a real nontechnical-admin acceptance test |
| Founding 10 acquisition | Consent-based application, attribution, signed email confirmation, duplicate privacy, metrics, retention commands | Public managed deployment, monitored privacy/support contacts, verified SMTP, real applicants; current verified count is tracked separately and must never be inferred from test data |
| Audit and retention | Append-only events, legal holds, retention preview/execute, tenant export | Organization-approved schedules, encrypted backup and restore evidence, incident rehearsal |
| CRM | Organization-scoped contacts, households, relationships, interactions, consent, sensitivity fields, basic create/list UI | Sample-spreadsheet import/correction/export acceptance, duplicate-resolution UX, charity vocabulary validation |
| Volunteers | Applications, profiles, skills, availability, review/promotion controls | Public applicant portal, configurable forms/waivers, complete recruitment-to-shift field test |
| Scheduling | Events, waitlist records, iCalendar export, tenant controls | Full recurrence/cancellation/reminder behavior, room conflicts, public booking, real coordinator acceptance |
| Documents and search | Upload limits, MIME/magic-byte/archive checks, extraction records, passages, scoped text search, legal-hold protection | Malware-scanner integration, OCR/Tika/Docling pipeline, semantic retrieval quality, permission/location acceptance corpus |
| AI gateway | Authenticated sidecar, Ollama chat/embedding adapters, deterministic fail-closed fallback, structured bounded operations, provenance fields, and a dated v1.6 live smoke pass with `qwen3:4b` plus `all-minilm` on one Windows host | Published task-specific evaluations, adversarial corpus expansion, broader hardware/model support matrix, real-user usefulness validation |
| Email assistant | Mailbox/message/draft records, polling command, explicit approval before SMTP send | Production IMAP/SMTP integration, cited-draft specialist UI, adversarial-message field test, retention approval |
| Analytics | Metric definitions, snapshots, summaries | Complete dashboards/exports and proof that each live metric has an owner, definition, date range, and reproducible query |
| Grants | Workspaces/questions, evidence fields, deterministic budget validation, bounded draft operation | Source-comparison drafting interface, version comparison/export, named-approver field workflow |
| Community resources | Service records, filters, provenance/freshness fields, verification action, scoped public endpoint | Map/geospatial production search, correction flow, freshness ownership and expired-record acceptance test |
| Translation | Jobs, memory/glossary records, review action, local/gateway adapter | Segment-comparison specialist UI, RTL review, bilingual reviewer acceptance, high-risk content policy test |
| Accessibility | Semantic responsive web foundation, visible focus, reduced-motion support, transformation/review records, and [v1.6 automated/browser-assisted evidence](accessibility-audit-v1.6.md) | Manual WCAG 2.2 AA audit, screen-reader/keyboard/zoom testing, tagged export validation, testing with users with disabilities |
| Installable web app | Manifest/service-worker shell connected to the hosted organization workspace; local record/note caching is intentionally excluded | Remote device/session administration, lost-device acceptance, and browser-install validation |
| Voice | Consent/call records, bounded intents, safety flags, callback/transfer state | Real telephony, speech-to-text/text-to-speech, unsupported/emergency live test; no production receptionist claim yet |
| Donor insights | Descriptive snapshots/cohorts, opt-out and reason fields | Independent ethics/privacy/fundraising review and production data-quality validation |
| Plugins | Catalogue/install records, declared permissions, capability-token issuance/revocation | Signed artefacts, SBOM verification, isolated runtime sandbox, malicious-plugin test; no marketplace claim yet |
| Public API | Tenant-scoped client records, one-time client secret, explicit scopes, resource endpoint | OAuth/OIDC client flow, signed webhooks, idempotency coverage, developer portal, schema fuzzing/BOLA suite |
| Mobile | Expo client, secure token storage, connected tenant API surfaces, fail-closed production URL configuration, and upgrade cleanup for legacy local record/note caches | Organization-owned Apple/Google signing, store review, device matrix and mobile accessibility acceptance |
| Desktop | Windows/macOS/Linux Electron installers, first-run workspace URL, update metadata | Organization-owned signing/notarization and warning-free distribution; public generic installers are currently unsigned |
| Operations | Development/production Compose, Gunicorn/Caddy, worker, local models, backup/restore scripts, setup helpers | Live production environment, pinned container digests, monitored backups, completed restore drill, incident/support rota |
| Managed commercial service | Founding Partner positioning and privacy-minimized pilot funnel | Hosted control plane, billing lifecycle, service terms/DPA, support tooling, operating entity/account, and verified paying customers |
| Repository licensing | Public source code | **No LICENSE file exists.** GitHub reports no license. The copyright owner must choose and approve a community/commercial licensing strategy before “open source” or reuse rights are claimed |

## Verification evidence

The quality gate runs Django checks, migration drift, Ruff, formatting, Mypy, Python dependency audit, SQLite and PostgreSQL suites, web tests/build, automated axe checks, mobile TypeScript/export/security mitigation, desktop build/audit, and development/production Compose validation. Native installer workflows build on all three operating systems for version tags.

The latest local verification for the team-onboarding change is recorded in its release notes and commit checks. On 2026-08-23, the live AI smoke suite also exercised classification, drafting, translation, plain-language rewriting, evidence-grounded grant answers, 384-dimension embeddings, and the deterministic crisis override against the configured local Ollama models. Test fixtures and demo accounts are synthetic and do not count as customers, pilots, external reviewers, or charity acceptance evidence.

## Release gate

A stable tag proves that the repository built and its automated gates passed. It does not prove a managed service is live, installers are signed, every optional runtime is connected, or charities have validated the workflows. Those claims require dated external evidence. The original PDF’s field-validation exit conditions remain open until that evidence is linked here.
