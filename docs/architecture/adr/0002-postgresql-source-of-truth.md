# ADR 0002: PostgreSQL is the initial source of truth

- Status: Accepted
- Date: 2026-07-31

## Context

Contacts, access control, schedules, audit, and future embeddings need relational joins and transactional consistency. A separate vector or geospatial database would increase operational cost.

## Decision

Use PostgreSQL with pgvector, and add PostGIS when resource search is implemented. Treat search indexes, embeddings, caches, and generated artifacts as rebuildable projections.

## Consequences

Backups and transactional authorization remain centralized. PostgreSQL must be sized and maintained correctly, and vector/geospatial extension versions must be pinned in deployment artifacts.

