# Security policy

Project Hope handles sensitive charity and service-user information. Please do not disclose suspected vulnerabilities in a public issue.

## Reporting

Send a private report to the repository maintainers with:

- affected component and version/commit;
- exact reproduction steps;
- impact and any exposed data;
- a minimal proof of concept where safe.

Do not include real client, donor, volunteer, or mailbox data.

## Release expectations

Before production use, operators must set a strong secret, enable HTTPS, configure trusted hosts and CSRF origins, use MFA-backed identity federation, restrict database access, encrypt disks/backups, test restore procedures, and review the threat model.

The deterministic AI adapter is not a safety certification. It is a bounded fallback and must remain behind the documented human-review controls.
