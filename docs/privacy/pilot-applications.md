# Founding 10 application privacy notice

Effective: 2026-08-23 · Notice version: `2026-08-23`

This notice covers the public Project Hope Founding 10 application form. It does not replace the privacy notice for a charity's operational workspace.

## Who is responsible

The organization operating the Project Hope deployment that contains the form is responsible for the application data. Before opening applications publicly, that operator must publish a monitored privacy contact and identify any hosting or email providers it uses.

## What the form collects

- contact name and work email;
- charity or nonprofit name;
- optional website and country or region;
- team size, primary need, and preferred service path;
- optional notes;
- consent to receive messages about the application;
- first-touch campaign fields and referring page, when present; and
- confirmation status, application stage, and timestamps.

The form does not request payment-card details, government identifiers, client records, beneficiary information, health information, or documents. Applicants should not place sensitive client information in the notes field.

## Why it is used

Application data is used only to confirm the request, assess pilot fit, communicate about scope and pricing, launch an agreed pilot, measure the acquisition funnel in aggregate, prevent abuse, and meet applicable operational or legal duties. It is not sold and is not used to train AI models.

## Confirmation and duplicate protection

Project Hope sends an expiring signed link to the supplied email address. A person counts as a verified applicant only after opening that link. Repeated submissions with the same normalized email do not create additional applicants and cannot overwrite the original application details.

## Access and disclosure

Only authorized deployment administrators can view application details. Other authenticated charity users cannot access them. The administrator metrics endpoint and `pilot_metrics` command return counts only—never names, email addresses, notes, or organization names.

Application data may pass through the operator's hosting and transactional-email providers solely to run the service. The deployment operator is responsible for naming those providers and selecting an appropriate hosting region before public launch.

## Retention

The background worker enforces the following defaults, which an operator may shorten:

- unverified applications: 14 days;
- declined applications: 90 days after the last update;
- verified applications that remain new, contacted, or qualified: 365 days after the last update; and
- active pilots and converted relationships: retained while needed for the active service relationship and then moved to a time-limited status by the operator.

The `purge_pilot_applications` command previews or executes the same rules. Backups follow the deployment's documented backup-expiry schedule.

## Choices and requests

An applicant may decline to submit the form or withdraw permission to be contacted. Requests to access, correct, export, or delete an application go to the privacy contact published by the deployment operator. Identity may need to be confirmed before a request is completed.

## Security

Project Hope uses HTTPS in production, rate limits, a bot honeypot, signed expiring confirmation tokens, normalized unique email records, restricted administrator access, generic duplicate responses, and privacy-safe aggregate metrics. No internet service can eliminate all risk; operators must also maintain secrets, backups, updates, monitoring, and incident contacts.
