# API plan

The API is versioned under `/api/v1/` and uses JSON. Browser clients use security-versioned Django sessions with CSRF protection; native and package clients use expiring, security-versioned DRF tokens. Enrolled accounts complete a short-lived, single-use TOTP/recovery challenge before either credential is created. Keycloak/OIDC federation remains an optional operator identity integration that maps into the same organization authorization service.

## Phase 1 endpoints

| Method | Path | Auth | Purpose |
|---|---|---|---|
| GET | `/api/v1/healthz/` | none | Liveness and database readiness |
| GET | `/api/v1/auth/csrf/` | none | Set/read CSRF cookie for browser clients |
| POST | `/api/v1/auth/login/` | none | Authenticate an active user by email/password |
| POST | `/api/v1/auth/token/` | none | Begin native sign-in; return a token only after any required MFA challenge |
| POST | `/api/v1/auth/mfa/challenge/` | none | Complete a single-use browser/native challenge with TOTP or a recovery code |
| GET | `/api/v1/auth/mfa/` | authenticated | Read enrollment policy and recovery-code status |
| POST | `/api/v1/auth/mfa/enrollment/` | authenticated + password | Begin private authenticator enrollment |
| POST | `/api/v1/auth/mfa/enrollment/confirm/` | authenticated | Confirm enrollment and return recovery codes once |
| POST | `/api/v1/auth/mfa/recovery-codes/` | password + MFA | Replace the recovery-code set |
| POST | `/api/v1/auth/mfa/disable/` | password + MFA | Disable the factor and supersede older credentials |
| POST | `/api/v1/auth/logout/` | session | End the current session |
| GET | `/api/v1/me/` | session | Current identity and organization memberships |
| GET | `/api/v1/organizations/` | session | List organizations for current user |
| POST | `/api/v1/organizations/` | session | Create organization and owner membership |
| GET | `/api/v1/organizations/{slug}/` | member | Retrieve a scoped organization |
| PATCH | `/api/v1/organizations/{slug}/` | owner/admin | Change organization name/status |
| GET | `/api/v1/organizations/{slug}/members/` | member | List memberships in one tenant |
| POST | `/api/v1/organizations/{slug}/members/` | owner/admin | Add an existing user to a tenant |
| PATCH | `/api/v1/organizations/{slug}/members/{id}/` | owner/admin | Change role/active status |
| GET | `/api/v1/organizations/{slug}/audit-events/` | owner/admin | Read tenant audit history |

## API invariants

- Browser write endpoints require CSRF protection; token-authenticated native clients do not use browser cookies.
- Production-required enrollment withholds organization metadata and blocks every organization endpoint until the account has an enabled factor. An enabled factor is enforced on every later sign-in even when the deployment-wide enrollment policy is optional.
- Object lookup is scoped to the authenticated user’s active memberships before serialization; unauthorized objects are not distinguishable from missing objects.
- Upload/body limits, DRF throttles, public-client rate limits, tenant scoping, and explicit public-client scopes are enforced before public resource reads.
- Cursor pagination, idempotency keys, property-level authorization, and signed webhooks remain extension points for future integrations that need them; the current public resource endpoint is intentionally bounded to 100 results.
