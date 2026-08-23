# Owner launch decisions

Project Hope 1.8 is published software. Turning it into a public managed service requires a small set of business and operating decisions that cannot be made safely in source code or inferred on the owner's behalf.

Do not put passwords, API keys, personal addresses, payment details, or signing certificates in this file or in the repository.

## Decisions required before public applications

| Decision | Practical pilot default | Evidence needed before launch |
|---|---|---|
| Service operator | Identify the legal person or entity that signs pilot terms, invoices, and responds to privacy requests. | Legal name, business address, monitored support/privacy route, and authorized signer. |
| Software licensing | Keep “Community preview—licensing pending” until the copyright owner and qualified counsel approve a license and commercial strategy. | Approved `LICENSE`, repository notices, and matching website/release language. |
| Hosting account and region | Use a dedicated operator-owned production account and a region accepted in writing by each pilot charity. | Provider, region, service-provider disclosure, access owners, and recovery route. |
| Public domain | Use one operator-controlled HTTPS domain for the web app and confirmation links. | Domain control, DNS, valid certificate, and exact `PROJECT_HOPE_PUBLIC_URL`. |
| Transactional email | Use an authenticated relay on a verified sending domain. | Successful delivery, expiry, retry, duplicate, and spam-placement tests. |
| Account security | Require Project Hope's built-in authenticator enrollment in production; store its dedicated encryption key in the operator's secret manager and define identity-checked recovery. Add an approved gateway or OIDC/SSO only when the charity requires it. | Clean-device enrollment/sign-in evidence, protected key backup, tested user/operator recovery, key-rotation result, short privileged sessions, and access review. |
| Privacy and service terms | Approve pilot terms, privacy notice, provider/subprocessor disclosure, data location, cancellation, and incident contacts. | Signed or accepted terms before a real workspace receives data. |
| Backups and incidents | Use encrypted backups in a separate failure domain and rehearse restoration. | Dated backup, restore, retention, alerting, and incident-response drill records. |
| Billing | Invoice the small founding cohort manually after a workspace is live; do not collect a card in the application. | Approved invoice identity/tax handling, written CAD $149 pilot terms, and payment reconciliation. |
| Desktop trust | Treat current generic installers as unsigned until code-signing identities are acquired. | Windows signing certificate, Apple Developer ID/notarization, signed artifacts, and clean-device install tests. |
| Mobile stores | Use organization-owned Apple and Google developer accounts if public mobile distribution is required. | Account ownership, privacy disclosures, signing, review approval, and store links. |

## Recommended first-pilot operating shape

- One dedicated production deployment owned by the operator, with PostgreSQL, Valkey, the AI gateway, model runtime, web app, API, worker, Caddy, and encrypted backups managed as one service.
- One charity workspace with a named owner and a synthetic-data onboarding rehearsal before any real import.
- Human-issued monthly invoices rather than building a card flow before legal identity, tax treatment, refunds, and customer terms are settled.
- A monitored support/privacy inbox and a documented escalation path.
- Weekly operator review of updates, backups, access, mail delivery, application metrics, and incidents.
- No high-sensitivity beneficiary data until the identity, privacy, accessibility, restore, and incident gates are signed off with the charity.

This pilot shape is deliberately operationally simple. It proves whether organizations will adopt and pay for the product before introducing a multi-tenant control plane or automated billing whose requirements depend on real customer evidence.

## Approval handoff

Before deployment, the owner should provide or approve:

- the operator/legal identity;
- the production hosting account and permitted region;
- the domain to configure;
- the transactional-email account and sending identity;
- the support and privacy contact route;
- the MFA encryption-key custody, account-recovery approvers, and any additional OIDC/SSO or gateway requirement;
- the license and pilot terms, after appropriate legal review;
- billing/invoice identity and tax treatment; and
- code-signing and mobile-store accounts when those channels are required.

Once those choices exist, follow the [production deployment guide](../operations/production-deployment.md), complete its synthetic launch rehearsal, and only then replace the private-message call to action with the public application URL.
