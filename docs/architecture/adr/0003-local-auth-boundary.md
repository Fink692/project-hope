# ADR 0003: Local Django authentication with a Keycloak boundary

- Status: Accepted
- Date: 2026-07-31

## Context

The research recommends Keycloak for self-hosted OIDC, OAuth, and SAML. A first milestone must also be runnable from a clean checkout without requiring federation setup.

## Decision

Phase 1 uses Django’s hardened password hashing and session authentication for local development and tests. The Podman topology includes Keycloak as the intended OIDC boundary. Authorization is implemented independently of the identity provider so OIDC claims can map into the same user and membership policy later.

## Consequences

The first milestone is easy to run and test, but local password auth is not the production identity posture. Production deployment must add Keycloak/OIDC, MFA, short privileged sessions, recovery codes, and removal/rotation of demo credentials before real sensitive data is loaded.

## 2026-08-23 amendment

Version 1.7 adds application-level TOTP enrollment and challenge verification, one-time recovery codes, encrypted/rotatable MFA secrets, and password/MFA security-version revocation for sessions and native tokens. Production requires this built-in factor and a shared security cache. Keycloak/OIDC is now an optional federation path for organizations that need SSO; independent authorization review, privileged-session policy, phishing-resistant factors, and removal/rotation of demo credentials remain production gates.
