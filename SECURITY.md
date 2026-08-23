# Security policy

Project Hope handles sensitive charity and service-user information. Please do not disclose suspected vulnerabilities in a public issue.

## Reporting

Use [GitHub private vulnerability reporting](https://github.com/Fink692/project-hope/security/advisories/new) to send the repository maintainers:

- affected component and version/commit;
- exact reproduction steps;
- impact and any exposed data;
- a minimal proof of concept where safe.

Do not include real client, donor, volunteer, or mailbox data.

## Release expectations

Before production use, operators must set a strong secret, enable HTTPS, configure trusted hosts and CSRF origins, use MFA-backed identity federation, restrict database access, encrypt disks/backups, test restore procedures, and review the threat model.

The deterministic AI adapter is not a safety certification. It is a bounded fallback and must remain behind the documented human-review controls.

## Dependency audit note

The 1.5.0 release audit reports no known production dependency vulnerabilities in the Python services, web client, or desktop client. Expo's Metro build chain still identifies `image-size` 1.2.1 under GHSA-w3rx-r6r6-pgpr and GHSA-5p2g-fcmc-qvqq; upstream currently publishes no patched package version. Project Hope therefore applies a locked pnpm patch that rejects undersized ISO BMFF boxes and zero-length ICNS entries, then runs `pnpm run test:security` in a worker with a hard timeout to prevent regressions. CI ignores only those two advisory IDs after that mitigation test passes. The affected parser is build tooling and is not used to process charity-uploaded documents at runtime.

The mobile lockfile also overrides the affected transitive `uuid` release to 11.1.1. Any removal of these controls must be reviewed against the current advisory state first.
