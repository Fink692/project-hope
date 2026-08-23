# Foundation data model

Phase 1 uses UUID primary keys and UTC timestamps. Future tenant-owned records must have a non-null `organization_id`, an access classification, and an explicit retention policy.

```text
User
  id UUID
  email unique
  password hash
  security version and last security-change timestamp
  name, active/staff flags, timestamps

MultiFactorCredential
  id UUID
  user_id -> User unique
  encrypted TOTP secret
  keyed recovery-code hashes and encryption-key identifier
  last accepted TOTP counter, enabled/updated timestamps

Organization
  id UUID
  name, slug unique, status, timestamps

Membership
  id UUID
  organization_id -> Organization
  user_id -> User
  role: owner | admin | coordinator | staff | viewer
  active flag, timestamps
  unique(organization, user)

AuditEvent
  id UUID
  organization_id -> Organization nullable for global events
  actor_id -> User nullable for system events
  event_type, action, resource_type, resource_id
  metadata JSON, request IP, user agent, created_at
```

## Invariants

- A user may read organization data only through an active membership.
- Membership role is evaluated server-side for every mutating endpoint.
- Organization IDs are not authorization credentials; membership is.
- Audit events cannot be updated or deleted through the application model/API.
- Audit metadata must not contain passwords, bearer tokens, complete prompts with personal data, raw mail bodies, or unrestricted document text.
- Authenticator secrets are encrypted with an operator-owned key; plaintext recovery codes are returned once and never stored. Password/MFA changes supersede older sessions and native tokens.
- Deactivation is preferred over destructive deletion until privacy workflows exist; later deletion must cover source files, vectors, search indexes, derived outputs, backups, and model-run metadata.
