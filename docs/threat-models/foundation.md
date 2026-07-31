# Foundation threat model

Scope: Phase 1 identity, organization APIs, memberships, audit events, local deployment, and future AI boundary. This is a design baseline, not a penetration-test report.

| Threat | Impact | Mitigation in Phase 1 | Residual risk / follow-up |
|---|---|---|---|
| Cross-tenant object access | Confidentiality breach | Membership-scoped query helpers, 404 for non-members, cross-tenant tests | Every future module must add the same matrix tests |
| Role escalation | Unauthorized administration | Central role policy, owner/admin checks, no client-controlled role grants | Add programme/field-level policy before CRM case data |
| Session theft/CSRF | Account takeover or unwanted writes | Django password hashing, session auth, CSRF middleware, secure-cookie production settings | MFA/short privileged sessions via Keycloak integration |
| Audit tampering | Loss of accountability | Append-only model behavior, restricted audit endpoint, no update/delete API | Hash chaining/immutable storage may be added for high-assurance deployments |
| Secret leakage in logs | Credential or personal-data exposure | Minimal audit metadata and explicit logging policy | Review every module’s log statements; add redaction tests |
| Malicious seed/default credentials | Local compromise | Development-only command, environment-controlled password, documentation warning | Production installer must require rotation and disable demo seed |
| Database exposure | Full tenant compromise | Local bind defaults, deployment docs, separate DB credentials | TLS/private networking and encrypted disks required in production |
| Malicious email/document prompt injection | Future unauthorized AI action | AI is absent in Phase 1; future gateway treats content as untrusted and uses schemas/approval | Must maintain adversarial corpus before AI promotion |
| Compromised plugin | Host/data compromise | No plugin runtime in Phase 1; future capability-only sandbox | Signed manifests, sandbox, network policy, kill switch before catalogue |
| DoS/resource exhaustion | Availability loss | Health endpoint and bounded future API design | Add rate limits, upload limits, queue quotas, monitoring |
| Privacy request incompleteness | Retained personal data | Data model and deletion requirements documented | Implement cross-store retention/deletion before production handling |

## Security defaults

Production must use a strong secret, HTTPS through Caddy, secure cookies, trusted hosts, MFA for staff/admins, encrypted disks/backups, restrictive database access, secret rotation, an incident contact tree, and explicit backup/restore testing. Development defaults are convenient, not safe for real sensitive records.

