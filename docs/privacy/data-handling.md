# Data handling and privacy baseline

Project Hope should hold only data tied to a defined programme purpose. Optional fields must be visibly optional. Sensitive fields and documents will eventually be labelled `public`, `internal`, `confidential`, `highly_sensitive`, or `restricted` and those labels will drive retrieval and UI policy.

Phase 1 stores identity, organization, membership, and audit data. It does not ingest mailboxes, documents, contacts, donations, volunteer applications, recordings, or model-training data.

## Rules for future modules

- Keep source identifiers and approved summaries rather than indefinite copies of whole mailboxes.
- Disable voice recording by default; transcripts need explicit retention periods and consent.
- Do not train or fine-tune models on charity data by default.
- Make AI opt-out and correction possible where practical; corrections are not silently training data.
- Privacy requests must cover relational data, files, vectors, search indexes, derived outputs, backups, and model-run metadata.
- Retention expiry must create an auditable deletion job, with legal holds represented explicitly.
- Never log raw passwords, bearer tokens, complete prompts containing personal information, unrestricted email bodies, or document text.

