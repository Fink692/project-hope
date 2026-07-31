# Project Hope requirements summary

Source of truth: the Project Hope research report supplied as `Project Hope_ A Zero-Cost, Self-Hosted AI Platform for Charities.pdf`, together with the implementation brief in the attached prompt.

## Functional requirements

1. Provide self-hosted identity, organizations, memberships, and role-based authorization.
2. Enforce tenant isolation on every tenant-owned query and record.
3. Record security-relevant actions in append-only audit events.
4. Provide a health endpoint for local and operational checks.
5. Seed a safe, repeatable development organization and administrator.
6. Provide an accessible web shell that works when AI is disabled.
7. Establish a modular-monolith structure that can later host CRM, volunteers, scheduling, documents, email, analytics, grants, resources, PWA, voice, donor insights, and plugins.
8. Support a local single-node deployment with PostgreSQL/pgvector, Keycloak, Valkey, Caddy, and test mail services without requiring paid services.
9. Keep AI behind a replaceable gateway and bounded task workflows; no model may perform side effects directly.
10. Maintain documentation, tests, migrations, and explicit phase gates.

## Non-functional requirements

- Strong organization and programme scoping, with no cross-tenant leakage.
- Least-privilege roles and explicit authentication state.
- UUID identifiers for externally visible domain records.
- Sensitive values excluded from logs and audit metadata.
- Accessible WCAG 2.2 AA target across the product, with automated checks supplemented by manual testing.
- Local-first storage, encrypted backups, retention controls, and deletion workflows as later domain modules arrive.
- Reproducible development and deployment configuration.
- No paid API, cloud subscription, or hosted identity provider as a hard dependency.
- Clear security limitations documented instead of implied guarantees.

## Contradictions and decisions

### Local authentication versus Keycloak

The report recommends Keycloak, while a useful first milestone must also start with one command on a developer machine. Phase 1 therefore implements Django session authentication with a custom email-based user model and includes Keycloak in the local service topology as the OIDC integration boundary. Keycloak federation and token validation are a follow-on identity milestone; business authorization is already independent of the authentication mechanism.

### PostgreSQL versus zero-dependency tests

Production and Podman use PostgreSQL with pgvector. The core test suite defaults to SQLite so unit and authorization tests can run without a database daemon. PostgreSQL integration checks remain part of the deployment/CI acceptance path.

### One foundation app versus future module boundaries

Identity and audit are separate Django apps now. Organization-scoped services are intentionally easy to extract later, but Phase 1 does not introduce microservices or duplicate databases.

### “Zero cost” meaning

The platform has no required paid software, hosted API, or cloud subscription. Hardware, electricity, connectivity, domain, email delivery, and public telephone access still have real costs and are explicitly outside the software guarantee.

