# Commercial readiness and Founding 10 runbook

Project Hope keeps its self-hosted software free. The paid product is a managed service that removes setup and maintenance work for charities.

## The offer

| Path | Price | Included |
|---|---:|---|
| Community | CAD $0 software | Self-hosted source, documentation, and release installers |
| Founding Partner | CAD $149/month during the pilot | Managed workspace launch, first-admin onboarding, updates, encrypted backups, and human support; no pilot setup fee |
| Partner Network | Scoped proposal | Rollout and governance for multiple charities |

The Founding Partner fee starts only after the workspace is live. Applying is free, no card is collected, and fit, scope, hosting region, data terms, and cancellation are confirmed in writing before launch. Pricing in future releases may change for new customers; an operator must honour any written pilot agreement already made.

## What “10 signed up” means

Project Hope does not count demo fixtures, seeded records, tests, repeated submissions, purchased lists, or unconfirmed email addresses.

The acquisition stages are:

1. `application` — a unique normalized email was captured with consent;
2. `verified` — the applicant opened the expiring email link;
3. `qualified` — a human confirmed the organization and use case are a fit;
4. `pilot` — a workspace and written pilot agreement are active; and
5. `converted` — the organization is a paying customer.

The Founding 10 headline metric is ten unique, email-verified applicants. Commercial traction should additionally report qualified, active-pilot, and converted counts so interest is never presented as revenue.

Administrators can inspect privacy-safe evidence with:

```powershell
cd services/core
python manage.py pilot_metrics
```

The equivalent authenticated endpoint is `GET /api/v1/pilot-applications/metrics/`. Detailed records remain in Django administration and are never returned by the public API.

## Public launch checklist

- Deploy the production topology behind a real HTTPS domain.
- Set `PROJECT_HOPE_PUBLIC_URL` to that exact public origin.
- Configure an authenticated transactional SMTP service and test delivery, confirmation, expiry, and spam placement.
- Publish a monitored privacy/support contact and identify the deployment operator and service providers.
- Run migration `identity.0002_pilotapplication` and confirm the worker is active.
- Submit one synthetic application, confirm it, verify aggregate metrics, then remove the synthetic record before launch.
- Test keyboard-only use, mobile layout, screen-reader labels, reduced motion, and 200% zoom.
- Confirm backup encryption, restore, incident response, and application-retention execution.
- Use a campaign URL such as `https://YOUR-DOMAIN/?utm_source=linkedin&utm_medium=social&utm_campaign=founding-10#founding-10`.
- Respond personally, record status truthfully, and never manufacture applicant or customer counts.

## Operating the funnel

Review new verified applications in Django administration. Update status only after the corresponding human event occurs. The recommended sequence is `new → contacted → qualified → pilot → converted`; use `declined` when the programme is not a fit or the applicant withdraws.

The public response is deliberately identical for first and repeated submissions. This prevents email-address enumeration. A repeated unverified request can receive another confirmation email but cannot alter the original record. Once verified, repeated requests do not trigger more mail.

## Evidence required before claiming traction

For any public progress claim, retain a dated privacy-safe output from `pilot_metrics`, the deployment release identifier, and a confirmation that synthetic records were excluded. Revenue claims require separate payment or signed-agreement evidence; application status alone is not proof of revenue.
