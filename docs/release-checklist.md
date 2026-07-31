# Release checklist

Project Hope is released only when the following gates are green:

- [ ] Django system and migration checks
- [ ] Ruff lint/format and Mypy
- [ ] Backend tests on SQLite and PostgreSQL/pgvector
- [ ] Web tests and production build
- [ ] Mobile frozen install and TypeScript check
- [ ] Compose configuration validation and clean startup
- [ ] HTTPS, strong secret, trusted hosts, CSRF origins, secure cookies, and MFA identity
- [ ] Backup restore test completed, including media and database
- [ ] Retention preview reviewed; legal holds confirmed
- [ ] Manual keyboard, screen-reader, reduced-motion, high-contrast, and mobile checks
- [ ] Threat-model review and incident contacts confirmed
- [ ] Model, OCR, translation, speech, and telephony adapters tested locally if enabled
- [ ] A staging smoke test completed with synthetic data
- [ ] Production topology validated from `deploy/podman/compose.production.yml`

The development compose file intentionally does not satisfy the production security gates by itself.
