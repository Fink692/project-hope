# Repository structure

```text
project-hope/
├── apps/
│   ├── web/                    # React/TypeScript/Vite accessible web workspace
│   └── mobile/                 # Expo/React Native bounded field client
├── services/
│   ├── core/                   # Django modular monolith and DRF API
│       ├── audit/              # append-only audit event boundary
│       ├── identity/           # users, organizations, memberships, policy
│       └── modules/             # CRM through plugins, workflows, adapters, commands
│       └── project/            # settings, URLs, health, WSGI/ASGI
│   └── ai-gateway/             # bounded local FastAPI adapter
├── deploy/
│   ├── podman/                 # PostgreSQL, Keycloak, Valkey, Mailpit, Caddy, app services
│   └── systemd/                # encrypted backup services for Linux/Windows operators
├── models/registry/             # machine-readable model licence/policy records
├── packages/                   # shared API client and JSON schemas
├── docs/
│   ├── architecture/           # overview, data model, agent flow, ADRs
│   ├── operations/             # local setup and operational cautions
│   ├── privacy/                # data minimization and retention baseline
│   └── threat-models/           # security and AI threat baseline
└── packages/                   # reserved for shared API schemas and client SDKs
```

Future module boundaries should be added as Django apps under `services/core` first. A separate service or database requires an ADR showing a concrete resource, security, or dependency reason.
