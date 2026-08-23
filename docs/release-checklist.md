# Release checklist

Project Hope is released only when the following gates are green:

- [ ] Django system and migration checks
- [ ] Ruff lint/format and Mypy
- [ ] Backend tests on SQLite and PostgreSQL/pgvector
- [ ] Web tests and production build
- [ ] Mobile frozen install and TypeScript check
- [ ] Compose configuration validation and clean startup
- [ ] HTTPS, separate Django/MFA secrets, trusted hosts, CSRF origins, secure cookies, shared Valkey cache, and required MFA enrollment
- [ ] Clean-device browser/native MFA, one-time recovery-code, operator reset, and encryption-key rotation rehearsals
- [ ] Backup restore test completed, including media and database
- [ ] Retention preview reviewed; legal holds confirmed
- [ ] Manual keyboard, screen-reader, reduced-motion, high-contrast, and mobile checks
- [ ] Threat-model review and incident contacts confirmed
- [ ] Model, OCR, translation, speech, and telephony adapters tested locally if enabled
- [ ] A staging smoke test completed with synthetic data
- [ ] Production topology validated from `deploy/podman/compose.production.yml`

The development compose file intentionally does not satisfy the production security gates by itself.
