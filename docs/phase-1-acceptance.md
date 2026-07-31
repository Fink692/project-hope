# Phase 1 acceptance criteria

Phase 1 is complete only when all criteria below are met.

1. A new developer can install the documented Python and Node dependencies.
2. `python manage.py migrate` completes from an empty database.
3. `python manage.py check` passes.
4. `python manage.py seed_demo` is idempotent and creates one organization, one owner membership, and a usable development login.
5. `GET /api/v1/healthz/` returns a healthy response without authentication and reports database readiness.
6. A user can log in, retrieve `/api/v1/me/`, and log out through the API.
7. An authenticated user can create an organization and becomes its owner.
8. A user can list and retrieve only organizations where they have an active membership.
9. Viewer users can read their organization but cannot change organization settings or memberships.
10. Owner/admin users can view organization audit events; other roles cannot.
11. Cross-tenant tests demonstrate that a member of organization A cannot retrieve organization B or its audit events.
12. Login, logout, organization creation, and membership changes create audit events without recording passwords or bearer tokens.
13. The web shell builds and contains an accessible navigation landmark, skip link, status region, and keyboard-visible focus styles.
14. Podman configuration contains the local database, identity boundary, cache/queue, test mail, backend, frontend, and reverse proxy services.
15. Documentation states what is implemented, what is deferred, and the security limitations of local development defaults.

