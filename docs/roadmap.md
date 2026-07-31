# Phased implementation roadmap

The roadmap is milestone-gated. All planned product phases below now have a functional, self-hosted, release-hardened implementation in this repository. Optional model, OCR, telephony, identity-federation, and publishing runtimes remain operator integrations because their credentials, hardware, and policy choices belong to each charity.

## Completion status

Phases 1–10 are implemented in the current product. The authoritative module-by-module evidence is in [full-build-status.md](full-build-status.md). Consequential operations remain bounded, audited, reviewable, or disabled until an operator explicitly enables the relevant integration.

## Phase 1 — Foundation (complete)

Repository, local stack, backend/frontend product shell, local authentication, organizations, memberships, roles, tenant isolation, audit events, health checks, seed data, tests, and exact setup documentation.

## Phase 2 — CRM core (complete)

Contacts, households, organizations, relationships, consent, interactions, configurable tags, import/export, duplicate review, sensitivity labels, and audit coverage.

## Phase 3 — Volunteer and scheduling core (complete)

Volunteer applications, onboarding, skills, availability, shifts, appointments, recurrence, reminders, attendance, waivers, and accessible exports.

## Phase 4 — Document platform (complete)

Secure uploads with size, MIME, magic-byte, archive traversal, archive member, and decompression-ratio checks; deterministic extraction; permission-aware passages; indexing; citations; and audited deletion/retention workflows. Optional malware/OCR/Tika sidecars remain isolated integrations.

## Phase 5 — AI gateway and email drafting (complete)

Local model registry, bounded operations, permission-aware retrieval, structured validators, prompt-injection tests, IMAP ingestion, cited drafts, and explicit send approval.

## Phase 6 — Analytics and grant workspace (complete)

Owned metric definitions, tested reporting views, accessible dashboards, grant evidence, citations, budget arithmetic, versioning, and named approval.

## Phase 7 — Resource directory, translation, and accessibility transformations (complete)

Open Referral-compatible resources, verification/freshness, geospatial search, segment translation, glossary, plain-language and audio transformations, bilingual and disability-led validation.

## Phase 8 — PWA and offline workflows (complete)

Bounded secure-storage snapshots with expiry, volunteer field surfaces, remote sign-out, offline notes, and low-bandwidth behavior.

## Phase 9 — Voice and donor-insights pilots (complete bounded implementation)

Only after safety review: browser/internal voice with human escalation and descriptive donor cohorts. No emergency counselling, vulnerability scoring, wealth estimation, or automated differential treatment.

## Phase 10 — Private plugin catalogue and native mobile (complete governance/client implementation)

Signed manifests, capability tokens, sandboxed execution, revocation, incident drills, and only then native mobile distribution. A public marketplace is last.
