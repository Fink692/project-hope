# Data handling and privacy baseline

Project Hope should hold only data tied to a defined programme purpose. Optional fields are visibly optional. Organization boundaries, role checks, consent records, legal holds, and append-only security events apply across the implemented operational modules.

The platform can store identity and membership data, contacts, volunteers, schedules, documents and extracted passages, minimized mailbox records and approved drafts, grants, resources, translations, analytics, voice-workflow metadata, donor snapshots, plugin/API configuration, and reviewable AI workflow records. Deployments must enable only the modules they can govern, publish their own purposes and retention periods, and avoid importing real data until the corresponding access, backup, export, and incident procedures pass staging verification.

The public Founding 10 form is a separate acquisition purpose. Its fields, confirmation boundary, access controls, and automated retention are documented in [the pilot application privacy notice](pilot-applications.md).

## Data-handling rules

- Keep source identifiers and approved summaries rather than indefinite copies of whole mailboxes.
- Disable voice recording by default; transcripts need explicit retention periods and consent.
- Do not train or fine-tune models on charity data by default.
- Make AI opt-out and correction possible where practical; corrections are not silently training data.
- Privacy requests must cover relational data, files, vectors, search indexes, derived outputs, backups, and model-run metadata.
- Retention expiry must create an auditable deletion job, with legal holds represented explicitly.
- Never log raw passwords, bearer tokens, complete prompts containing personal information, unrestricted email bodies, or document text.
