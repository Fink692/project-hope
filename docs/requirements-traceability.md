# Requirements traceability matrix

Status is evidence-based: **implemented** means tested code exists; **partial** means a baseline exists but an original exit condition remains open; **open** means the capability is absent or unproven.

| ID | Requirement | Current evidence | Status / open gate |
|---|---|---|---|
| R-01 | Self-hosted baseline | Compose topology, Django/PostgreSQL, web and local Ollama services | Implemented baseline; production operator controls remain |
| R-02 | Authentication | Email user, hashed passwords, session/token login, expiring invitations, one-time account recovery | Partial: OIDC/MFA is open |
| R-03 | Organizations and memberships | Organization, Membership, bootstrap command, Team & access UI | Implemented; nontechnical-admin acceptance is open |
| R-04 | Role-based authorization | Owner/admin/coordinator/staff/viewer policy and authorization tests | Implemented baseline; independent review is open |
| R-05 | Tenant isolation | Organization membership required before scoped lookup; cross-tenant tests | Implemented baseline; broader BOLA/fuzz test is open |
| R-06 | Audit foundation | Append-only event model and auth/org/member/invitation events | Implemented baseline; operational retention/export review is open |
| R-07 | Health checks | Public core/database/AI readiness endpoint | Implemented |
| R-08 | Safe first setup | Demo seed for training; production owner invitation command | Implemented; live SMTP/operator acceptance is open |
| R-09 | Accessible web foundation | Landmarks, focus, reflow styles, reduced motion, axe tests | Partial: manual WCAG/user testing is open |
| R-10 | Useful with AI disabled | Core organization and records paths do not require model output | Implemented baseline |
| R-11 | Replaceable bounded AI gateway | Sidecar adapter, Ollama and deterministic paths, provenance | Partial: published evaluations and external runtimes are open |
| R-12 | Human approval before consequences | Workflow, email, translation, accessibility review gates | Implemented baseline; field/adversarial acceptance remains open |
| R-13 | Privacy, retention, deletion | Sensitivity, legal holds, retention command, export, audit | Partial: policy approval and restore evidence are open |
| R-14 | Threat model | Foundation threat model and residual-risk documentation | Partial: independent security assessment is open |
| R-15 | Automated verification | CI for backend/PostgreSQL/web/mobile/desktop/Compose and audits | Implemented for repository paths; external systems are not covered |
| R-16 | Specialist module exit conditions | Domain models and bounded APIs across the named modules | Partial: see `full-build-status.md` for each unproven field gate |
| R-17 | Managed service and payment | Pilot application and pricing copy | Open: hosting, billing, legal/service operations and customers |
| R-18 | Software licensing | No license metadata or LICENSE file | Open: owner decision required |
