# Architecture overview

Project Hope starts as a modular monolith to keep memory use, deployment, and security review realistic for small charities. Django is the transactional domain core; React is a static accessible client; PostgreSQL is the source of truth; background workers and AI/document/voice runtimes are sidecars only when their dependencies justify separation.

```text
Browser / PWA
      |
      v
    Caddy  ---- TLS and reverse proxy
      |
      +--> React/Vite web shell
      |
      +--> Django + DRF modular monolith
                |
                +--> identity and organization policy
                +--> audit event service
                +--> future CRM, volunteer, schedule, document, email modules
                +--> future bounded AI gateway
                |
                +--> PostgreSQL + pgvector + PostGIS
                +--> Valkey / Celery workers
                +--> local filesystem or S3-compatible object storage

Optional sidecars: Keycloak, document conversion, AI inference, voice gateway, Meilisearch.
```

## Boundary rules

- All business modules use organization-scoped query helpers and authorization checks; they never trust a client-supplied organization ID by itself.
- Authentication identifies a user. Authorization is enforced by Project Hope using active organization memberships, role, programme scope, field sensitivity, consent, and policy.
- The database is the source of truth. Search indexes, embeddings, caches, and generated files are rebuildable projections.
- AI services receive bounded structured requests and return validated structured results. They do not receive database credentials or arbitrary tools.
- Side effects are deterministic application operations reached only after an explicit approval state.
- Audit events are append-only and record actor, tenant, action, resource, request context, and minimal metadata.

## Phase 1 structure

The first milestone contains two Django apps:

- `identity`: custom user, organization, membership, authentication endpoints, organization-scoped API, and role policy.
- `audit`: append-only event record, event manager, and administrator-readable organization audit endpoint.

This is intentionally smaller than the eventual module map. The seams are real Django app boundaries and shared service contracts, not prematurely deployed services.

