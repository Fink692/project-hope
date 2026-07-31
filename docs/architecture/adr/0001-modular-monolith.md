# ADR 0001: Start with a modular monolith

- Status: Accepted
- Date: 2026-07-31

## Context

The target charity is expected to have roughly ten staff, five concurrent users, hundreds of volunteers, and modest document volume. Small charities need a system that can be installed and repaired by a small team.

## Decision

Use one Django deployment and one PostgreSQL database with explicit Django app/module boundaries. Run background jobs and model/document/voice runtimes as sidecars only when their dependency or resource profile warrants it.

## Consequences

This minimizes operational and security complexity and keeps transactions coherent. It requires discipline around app boundaries and can be split later if scale or isolation justifies it. Kubernetes is deferred until there are multiple physical nodes or a real availability requirement.

