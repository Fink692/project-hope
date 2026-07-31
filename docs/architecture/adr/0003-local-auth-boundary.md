# ADR 0003: Local Django authentication with a Keycloak boundary

- Status: Accepted
- Date: 2026-07-31

## Context

The research recommends Keycloak for self-hosted OIDC, OAuth, and SAML. A first milestone must also be runnable from a clean checkout without requiring federation setup.

## Decision

Phase 1 uses Django’s hardened password hashing and session authentication for local development and tests. The Podman topology includes Keycloak as the intended OIDC boundary. Authorization is implemented independently of the identity provider so OIDC claims can map into the same user and membership policy later.

## Consequences

The first milestone is easy to run and test, but local password auth is not the production identity posture. Production deployment must add Keycloak/OIDC, MFA, short privileged sessions, recovery codes, and removal/rotation of demo credentials before real sensitive data is loaded.

