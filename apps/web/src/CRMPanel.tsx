import { FormEvent, useEffect, useMemo, useState } from "react";

type Organization = {
  id: string;
  name: string;
  slug: string;
};

type Contact = {
  id: string;
  display_name: string;
  contact_type?: string;
  first_name?: string;
  last_name?: string;
  organization_name?: string;
  preferred_name?: string;
  email?: string;
  phone?: string;
  external_ref?: string;
  sensitivity?: string;
  consent_status?: string;
  notes?: string;
  record_status?: string;
};

type Candidate = {
  id: string;
  displayName: string;
  contactType: string;
  firstName: string;
  lastName: string;
  organizationName: string;
  email: string;
  phone: string;
  externalRef: string;
  sensitivity: string;
  consentStatus: string;
  updatedAt: string;
  matchReasons: string[];
};

type PreviewRow = {
  rowNumber: number;
  status: "new" | "exact_match" | "possible_duplicate" | "invalid";
  values: Record<string, string>;
  providedFields: string[];
  errors: Record<string, string[]>;
  candidates: Candidate[];
  recommendedAction: "create" | "skip";
};

type ImportPreview = {
  fileName: string;
  fileType: string;
  previewToken: string;
  expiresInSeconds: number;
  warnings: string[];
  summary: {
    totalRows: number;
    newRecords: number;
    exactMatches: number;
    possibleDuplicates: number;
    invalidRows: number;
  };
  rows: PreviewRow[];
};

type ImportResult = {
  created: number;
  updated: number;
  unchanged: number;
  skipped: number;
  invalid: number;
};

type DuplicatePair = {
  first: Candidate;
  second: Candidate;
  matchReasons: string[];
  confidence: "exact" | "strong" | "possible";
};

type DuplicateReview = {
  totalActiveContacts: number;
  totalCandidates: number;
  results: DuplicatePair[];
};

type ContactValues = {
  contact_type: string;
  first_name: string;
  last_name: string;
  organization_name: string;
  preferred_name: string;
  email: string;
  phone: string;
  external_ref: string;
  sensitivity: string;
  consent_status: string;
  notes: string;
};

const emptyContact: ContactValues = {
  contact_type: "person",
  first_name: "",
  last_name: "",
  organization_name: "",
  preferred_name: "",
  email: "",
  phone: "",
  external_ref: "",
  sensitivity: "internal",
  consent_status: "unknown",
  notes: "",
};

function readCookie(name: string) {
  return document.cookie
    .split("; ")
    .find((row) => row.startsWith(`${name}=`))
    ?.split("=")[1];
}

function responseError(body: unknown, status: number) {
  if (body && typeof body === "object") {
    const record = body as Record<string, unknown>;
    if (typeof record.detail === "string") return record.detail;
    const fields = Object.entries(record)
      .map(([key, value]) => `${key}: ${Array.isArray(value) ? value.join(", ") : String(value)}`)
      .join(" · ");
    if (fields) return fields;
  }
  return `Request failed (${status})`;
}

async function crmRequest<T>(path: string, init: RequestInit = {}): Promise<T> {
  const headers = new Headers(init.headers);
  if (init.body && !(init.body instanceof FormData) && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }
  const csrf = readCookie("csrftoken");
  if (csrf) headers.set("X-CSRFToken", csrf);
  const response = await fetch(path, { ...init, headers, credentials: "include" });
  const body = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(responseError(body, response.status));
  return body as T;
}

async function download(path: string) {
  const headers = new Headers();
  const csrf = readCookie("csrftoken");
  if (csrf) headers.set("X-CSRFToken", csrf);
  const response = await fetch(path, { headers, credentials: "include" });
  if (!response.ok) {
    const body = await response.json().catch(() => ({}));
    throw new Error(responseError(body, response.status));
  }
  const disposition = response.headers.get("Content-Disposition") ?? "";
  const match = disposition.match(/filename="?([^";]+)"?/i);
  const filename = (match?.[1] ?? "project-hope-contacts.xlsx").replace(/[\\/:*?"<>|]/g, "-");
  const blob = await response.blob();
  const href = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = href;
  anchor.download = filename;
  anchor.click();
  URL.revokeObjectURL(href);
}

function contactName(contact: Contact | Candidate) {
  if ("display_name" in contact) return contact.display_name;
  return contact.displayName;
}

function valuesFor(contact?: Contact): ContactValues {
  if (!contact) return { ...emptyContact };
  return {
    contact_type: contact.contact_type ?? "person",
    first_name: contact.first_name ?? "",
    last_name: contact.last_name ?? "",
    organization_name: contact.organization_name ?? "",
    preferred_name: contact.preferred_name ?? "",
    email: contact.email ?? "",
    phone: contact.phone ?? "",
    external_ref: contact.external_ref ?? "",
    sensitivity: contact.sensitivity ?? "internal",
    consent_status: contact.consent_status ?? "unknown",
    notes: contact.notes ?? "",
  };
}

function importedName(row: PreviewRow) {
  const preferred = row.values.preferred_name || row.values.first_name;
  return [preferred, row.values.last_name].filter(Boolean).join(" ")
    || row.values.organization_name
    || row.values.email
    || `Spreadsheet row ${row.rowNumber}`;
}

function statusLabel(status: PreviewRow["status"]) {
  return {
    new: "Ready to add",
    exact_match: "Existing match",
    possible_duplicate: "Possible duplicate",
    invalid: "Needs correction",
  }[status];
}

function candidateSummary(candidate: Candidate) {
  return [candidate.email, candidate.phone, candidate.externalRef && `Ref ${candidate.externalRef}`]
    .filter(Boolean)
    .join(" · ") || "No email or phone";
}

export default function CRMPanel({ organization, role }: { organization: Organization; role: string }) {
  const [activeView, setActiveView] = useState<"contacts" | "migration" | "duplicates">("contacts");
  const [contacts, setContacts] = useState<Contact[] | null>(null);
  const [query, setQuery] = useState("");
  const [submittedQuery, setSubmittedQuery] = useState("");
  const [contactError, setContactError] = useState("");
  const [refreshing, setRefreshing] = useState(false);
  const [showCreate, setShowCreate] = useState(false);
  const [editing, setEditing] = useState<Contact | null>(null);
  const [file, setFile] = useState<File | null>(null);
  const [preview, setPreview] = useState<ImportPreview | null>(null);
  const [actions, setActions] = useState<Record<number, string>>({});
  const [importBusy, setImportBusy] = useState(false);
  const [importError, setImportError] = useState("");
  const [importResult, setImportResult] = useState<ImportResult | null>(null);
  const [downloadBusy, setDownloadBusy] = useState("");
  const [duplicates, setDuplicates] = useState<DuplicateReview | null>(null);
  const [duplicatesBusy, setDuplicatesBusy] = useState(false);
  const [duplicateError, setDuplicateError] = useState("");
  const [mergeNotice, setMergeNotice] = useState("");
  const canEdit = ["owner", "admin", "coordinator", "staff"].includes(role);
  const canAdminister = ["owner", "admin"].includes(role);
  const base = `/api/v1/organizations/${organization.slug}`;

  async function loadContacts(nextQuery = submittedQuery) {
    setContactError("");
    try {
      const suffix = nextQuery ? `?q=${encodeURIComponent(nextQuery)}` : "";
      setSubmittedQuery(nextQuery);
      setContacts(await crmRequest<Contact[]>(`${base}/contacts/${suffix}`));
    } catch (reason) {
      setContactError(reason instanceof Error ? reason.message : "Unable to load contacts.");
      setContacts([]);
    }
  }

  useEffect(() => {
    setActiveView("contacts");
    setFile(null);
    setPreview(null);
    setImportResult(null);
    setDuplicates(null);
    setMergeNotice("");
    void loadContacts("");
  }, [organization.slug]);

  async function refreshContacts() {
    setRefreshing(true);
    await loadContacts();
    setRefreshing(false);
  }

  async function chooseView(view: "contacts" | "migration" | "duplicates") {
    setActiveView(view);
    if (view === "duplicates" && canAdminister && duplicates === null) await loadDuplicates();
  }

  async function previewFile(event: FormEvent) {
    event.preventDefault();
    if (!file) return;
    setImportBusy(true);
    setImportError("");
    setImportResult(null);
    try {
      const form = new FormData();
      form.append("file", file);
      const result = await crmRequest<ImportPreview>(`${base}/crm/imports/preview/`, {
        method: "POST",
        body: form,
      });
      setPreview(result);
      setActions(Object.fromEntries(result.rows.map((row) => [row.rowNumber, row.recommendedAction])));
    } catch (reason) {
      setPreview(null);
      setImportError(reason instanceof Error ? reason.message : "Unable to preview this file.");
    } finally {
      setImportBusy(false);
    }
  }

  function setRowAction(rowNumber: number, value: string) {
    setActions((current) => ({ ...current, [rowNumber]: value }));
  }

  async function commitImport() {
    if (!file || !preview) return;
    setImportBusy(true);
    setImportError("");
    try {
      const reviewedActions = preview.rows.map((row) => {
        const selected = actions[row.rowNumber] ?? "skip";
        if (selected.startsWith("update:")) {
          return { rowNumber: row.rowNumber, action: "update", targetContactId: selected.slice(7) };
        }
        return { rowNumber: row.rowNumber, action: selected };
      });
      const form = new FormData();
      form.append("file", file);
      form.append("previewToken", preview.previewToken);
      form.append("actions", JSON.stringify(reviewedActions));
      const result = await crmRequest<ImportResult>(`${base}/crm/imports/commit/`, {
        method: "POST",
        body: form,
      });
      setImportResult(result);
      setPreview(null);
      setFile(null);
      await loadContacts("");
    } catch (reason) {
      setImportError(reason instanceof Error ? reason.message : "Unable to import the reviewed rows.");
    } finally {
      setImportBusy(false);
    }
  }

  async function getDownload(kind: "template" | "export", format: "xlsx" | "csv") {
    setDownloadBusy(`${kind}-${format}`);
    setImportError("");
    try {
      await download(`${base}/crm/${kind}/?fileFormat=${format}`);
    } catch (reason) {
      setImportError(reason instanceof Error ? reason.message : "Unable to download this file.");
    } finally {
      setDownloadBusy("");
    }
  }

  async function loadDuplicates() {
    setDuplicatesBusy(true);
    setDuplicateError("");
    try {
      setDuplicates(await crmRequest<DuplicateReview>(`${base}/crm/duplicates/`));
    } catch (reason) {
      setDuplicateError(reason instanceof Error ? reason.message : "Unable to review duplicates.");
      setDuplicates({ totalActiveContacts: 0, totalCandidates: 0, results: [] });
    } finally {
      setDuplicatesBusy(false);
    }
  }

  async function mergePair(primaryContactId: string, duplicateContactId: string) {
    setDuplicatesBusy(true);
    setDuplicateError("");
    setMergeNotice("");
    try {
      await crmRequest(`${base}/crm/duplicates/merge/`, {
        method: "POST",
        body: JSON.stringify({ primaryContactId, duplicateContactId, confirm: true }),
      });
      setMergeNotice("The records were merged. The source record and its history were preserved.");
      await Promise.all([loadContacts(""), loadDuplicates()]);
    } catch (reason) {
      setDuplicateError(reason instanceof Error ? reason.message : "Unable to merge these contacts.");
      setDuplicatesBusy(false);
    }
  }

  const selectedImportCount = useMemo(
    () => Object.values(actions).filter((action) => action === "create" || action.startsWith("update:")).length,
    [actions],
  );

  return (
    <div className="crm-panel">
      <div className="module-heading">
        <div>
          <p className="eyebrow">People and relationships</p>
          <h3 className="module-title">CRM</h3>
          <p className="module-lede">Keep trusted contact details together, move safely from a spreadsheet, and correct duplicates without erasing history.</p>
        </div>
        <span className="module-count" aria-label={`${contacts?.length ?? 0} contacts`}>{contacts?.length ?? 0} contacts</span>
      </div>

      <nav className="crm-view-nav" aria-label="CRM views">
        <button aria-current={activeView === "contacts" ? "page" : undefined} className={activeView === "contacts" ? "selected" : ""} type="button" onClick={() => void chooseView("contacts")}>Contacts</button>
        {canAdminister && <button aria-current={activeView === "migration" ? "page" : undefined} className={activeView === "migration" ? "selected" : ""} type="button" onClick={() => void chooseView("migration")}>Import & export</button>}
        {canAdminister && <button aria-current={activeView === "duplicates" ? "page" : undefined} className={activeView === "duplicates" ? "selected" : ""} type="button" onClick={() => void chooseView("duplicates")}>Find duplicates</button>}
      </nav>

      {activeView === "contacts" && (
        <section aria-labelledby="contacts-title">
          <h4 className="sr-only" id="contacts-title">Contacts</h4>
          <div className="module-toolbar" role="search">
            <label className="search-field"><span className="sr-only">Search contacts</span><input value={query} onChange={(event) => setQuery(event.target.value)} onKeyDown={(event) => { if (event.key === "Enter") void loadContacts(query.trim()); }} placeholder="Search people, email, or phone" type="search" /></label>
            <button className="button secondary compact" type="button" onClick={() => void loadContacts(query.trim())}>Search</button>
            <button className="button secondary compact" disabled={refreshing} type="button" onClick={() => void refreshContacts()}>{refreshing ? "Refreshing…" : "Refresh"}</button>
            {canEdit && <button className="button primary compact" type="button" onClick={() => { setEditing(null); setShowCreate((value) => !value); }}>{showCreate && !editing ? "Close form" : "New record"}</button>}
          </div>
          {!canEdit && <p className="permission-note">You have view-only access. An owner, administrator, coordinator, or staff member can change contact records.</p>}
          {showCreate && !editing && <ContactForm organization={organization} onCancel={() => setShowCreate(false)} onSaved={() => { setShowCreate(false); void loadContacts(); }} />}
          {editing && <ContactForm contact={editing} organization={organization} onCancel={() => setEditing(null)} onSaved={() => { setEditing(null); void loadContacts(); }} />}
          {contactError ? <div className="empty-state error-state" role="alert"><strong>Could not load contacts.</strong><p>{contactError}</p><button className="button secondary compact" type="button" onClick={() => void loadContacts()}>Try again</button></div>
            : contacts === null ? <p className="loading-state" role="status">Loading contacts…</p>
              : contacts.length === 0 ? <div className="empty-state"><strong>{submittedQuery ? "No matching contacts." : "No contacts yet."}</strong><p>{submittedQuery ? "Try another name, email, or phone number." : canEdit ? "Add one contact or import a reviewed spreadsheet when you are ready." : "There are no active contact records to show."}</p></div>
                : <div className="contact-list">{contacts.map((contact) => <article key={contact.id}><div className="contact-avatar" aria-hidden="true">{contact.display_name.slice(0, 1).toUpperCase()}</div><div><strong>{contact.display_name}</strong><small>{[contact.email, contact.phone, contact.organization_name].filter(Boolean).join(" · ") || "No email or phone yet"}</small><span>{(contact.contact_type ?? "person").replaceAll("_", " ")} · {(contact.consent_status ?? "unknown").replaceAll("_", " ")} consent</span></div>{canEdit && <button aria-label={`Edit ${contact.display_name}`} className="text-button" type="button" onClick={() => { setShowCreate(false); setEditing(contact); }}>Edit</button>}</article>)}</div>}
        </section>
      )}

      {activeView === "migration" && canAdminister && (
        <section className="migration-workspace" aria-labelledby="migration-title">
          <div className="crm-section-heading"><div><p className="eyebrow">Guided move</p><h4 id="migration-title">Bring your contacts with you.</h4></div><p>Preview first. Nothing changes until you review every row and choose Import.</p></div>
          <ol className="migration-steps" aria-label="Import steps">
            <li className={!preview && !importResult ? "current" : "complete"}><span>1</span><div><strong>Choose</strong><small>CSV or Excel</small></div></li>
            <li className={preview ? "current" : importResult ? "complete" : ""}><span>2</span><div><strong>Review</strong><small>Errors and matches</small></div></li>
            <li className={importResult ? "complete" : ""}><span>3</span><div><strong>Finish</strong><small>See what changed</small></div></li>
          </ol>

          <div className="migration-tools">
            <article className="migration-card">
              <span className="card-number">Start clean</span>
              <h5>Use our ready-made template</h5>
              <p>Open it in Excel, Google Sheets, or LibreOffice. Helpful dropdowns and a plain-language guide are included.</p>
              <div className="form-actions"><button className="button secondary compact" disabled={Boolean(downloadBusy)} type="button" onClick={() => void getDownload("template", "xlsx")}>{downloadBusy === "template-xlsx" ? "Preparing…" : "Excel template"}</button><button className="text-button" disabled={Boolean(downloadBusy)} type="button" onClick={() => void getDownload("template", "csv")}>CSV template</button></div>
            </article>
            <article className="migration-card">
              <span className="card-number">Keep a copy</span>
              <h5>Export whenever you need it</h5>
              <p>Download all active contacts in an open spreadsheet format. Your organization stays in control of its data.</p>
              <div className="form-actions"><button className="button secondary compact" disabled={Boolean(downloadBusy)} type="button" onClick={() => void getDownload("export", "xlsx")}>{downloadBusy === "export-xlsx" ? "Preparing…" : "Export Excel"}</button><button className="text-button" disabled={Boolean(downloadBusy)} type="button" onClick={() => void getDownload("export", "csv")}>Export CSV</button></div>
            </article>
          </div>

          <form className="import-picker" onSubmit={previewFile}>
            <div><label htmlFor="crm-import-file">Contact file</label><p>Choose a .xlsx, .csv, or .tsv file up to 5 MB and 2,500 contact rows.</p></div>
            <input accept=".xlsx,.csv,.tsv" id="crm-import-file" key={importResult ? "finished" : "ready"} onChange={(event) => { setFile(event.target.files?.[0] ?? null); setPreview(null); setImportResult(null); setImportError(""); }} required type="file" />
            <button aria-busy={importBusy} className="button primary compact" disabled={importBusy || !file} type="submit">{importBusy && !preview ? "Checking file…" : "Preview contact file"}</button>
          </form>
          {importError && <p className="form-error migration-error" role="alert">{importError}</p>}
          {importResult && <div className="import-success" role="status" aria-live="polite"><span aria-hidden="true">✓</span><div><p className="eyebrow">Import complete</p><h5>Your contacts are ready.</h5><p>{importResult.created} added · {importResult.updated} filled in · {importResult.unchanged} already complete · {importResult.skipped} skipped.</p></div><button className="button secondary compact" type="button" onClick={() => void chooseView("contacts")}>View contacts</button></div>}

          {preview && <ImportReview preview={preview} actions={actions} busy={importBusy} selectedCount={selectedImportCount} onAction={setRowAction} onCancel={() => { setPreview(null); setActions({}); }} onCommit={() => void commitImport()} />}
        </section>
      )}

      {activeView === "duplicates" && canAdminister && (
        <section className="duplicate-workspace" aria-labelledby="duplicates-title">
          <div className="crm-section-heading"><div><p className="eyebrow">Careful cleanup</p><h4 id="duplicates-title">Review possible duplicates.</h4></div><p>Merging keeps one active contact, preserves the other as a source record, and moves linked history safely.</p></div>
          <div className="duplicate-toolbar"><p>{duplicates ? `${duplicates.totalCandidates} possible ${duplicates.totalCandidates === 1 ? "pair" : "pairs"} across ${duplicates.totalActiveContacts} active contacts` : "Checking active contacts…"}</p><button className="button secondary compact" disabled={duplicatesBusy} type="button" onClick={() => void loadDuplicates()}>{duplicatesBusy ? "Checking…" : "Check again"}</button></div>
          {mergeNotice && <p className="success-notice" role="status" aria-live="polite">{mergeNotice}</p>}
          {duplicateError && <p className="form-error" role="alert">{duplicateError}</p>}
          {duplicatesBusy && duplicates === null ? <p className="loading-state" role="status">Looking for possible duplicates…</p>
            : duplicates?.results.length === 0 ? <div className="empty-state"><strong>No likely duplicates found.</strong><p>Project Hope checked exact email, external reference, full name, organization name, and name with phone.</p></div>
              : <div className="duplicate-list">{duplicates?.results.map((pair) => <DuplicatePairCard disabled={duplicatesBusy} key={`${pair.first.id}-${pair.second.id}`} pair={pair} onMerge={mergePair} />)}</div>}
        </section>
      )}
    </div>
  );
}

function ContactForm({ contact, organization, onCancel, onSaved }: { contact?: Contact; organization: Organization; onCancel: () => void; onSaved: () => void }) {
  const [values, setValues] = useState<ContactValues>(() => valuesFor(contact));
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");

  function update(name: keyof ContactValues, value: string) {
    setValues((current) => ({ ...current, [name]: value }));
  }

  async function save(event: FormEvent) {
    event.preventDefault();
    setSaving(true);
    setError("");
    try {
      const path = contact
        ? `/api/v1/organizations/${organization.slug}/contacts/${contact.id}/`
        : `/api/v1/organizations/${organization.slug}/contacts/`;
      await crmRequest(path, { method: contact ? "PATCH" : "POST", body: JSON.stringify(values) });
      onSaved();
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Unable to save this contact.");
    } finally {
      setSaving(false);
    }
  }

  return (
    <form className="record-form contact-form" onSubmit={save} aria-label={contact ? `Edit ${contact.display_name}` : "Create contacts record"}>
      <div className="form-title"><div><p className="eyebrow">{contact ? "Correct contact" : "New contact"}</p><h4>{contact ? `Edit ${contact.display_name}` : "Add one person or organization"}</h4></div><button className="text-button" type="button" onClick={onCancel}>Cancel</button></div>
      <div className="form-grid">
        <label>Record type<select value={values.contact_type} onChange={(event) => update("contact_type", event.target.value)}><option value="person">Person</option><option value="organization">Organization</option><option value="service_user">Service user</option><option value="donor">Donor</option><option value="volunteer">Volunteer</option></select></label>
        <label>Preferred name<input value={values.preferred_name} onChange={(event) => update("preferred_name", event.target.value)} /></label>
        <label>First name<input autoComplete="given-name" value={values.first_name} onChange={(event) => update("first_name", event.target.value)} /></label>
        <label>Last name<input autoComplete="family-name" value={values.last_name} onChange={(event) => update("last_name", event.target.value)} /></label>
        <label>Organization name<input autoComplete="organization" value={values.organization_name} onChange={(event) => update("organization_name", event.target.value)} /></label>
        <label>Email<input autoComplete="email" type="email" value={values.email} onChange={(event) => update("email", event.target.value)} /></label>
        <label>Phone<input autoComplete="tel" type="tel" value={values.phone} onChange={(event) => update("phone", event.target.value)} /></label>
        <label>External reference<input value={values.external_ref} onChange={(event) => update("external_ref", event.target.value)} /></label>
        <label>Sensitivity<select value={values.sensitivity} onChange={(event) => update("sensitivity", event.target.value)}><option value="public">Public</option><option value="internal">Internal</option><option value="confidential">Confidential</option><option value="highly_sensitive">Highly sensitive</option><option value="restricted">Restricted</option></select></label>
        <label>Consent<select value={values.consent_status} onChange={(event) => update("consent_status", event.target.value)}><option value="unknown">Unknown</option><option value="granted">Granted</option><option value="withdrawn">Withdrawn</option></select></label>
        <label>Notes<textarea value={values.notes} onChange={(event) => update("notes", event.target.value)} /></label>
      </div>
      <p className="identity-hint">Add at least a name, organization, email, phone, or external reference.</p>
      {error && <p className="form-error" role="alert">{error}</p>}
      <div className="form-actions"><button aria-busy={saving} className="button primary compact" disabled={saving} type="submit">{saving ? "Saving…" : "Save record"}</button><span className="form-hint">Saved inside {organization.name} only.</span></div>
    </form>
  );
}

function ImportReview({ preview, actions, busy, selectedCount, onAction, onCancel, onCommit }: { preview: ImportPreview; actions: Record<number, string>; busy: boolean; selectedCount: number; onAction: (row: number, action: string) => void; onCancel: () => void; onCommit: () => void }) {
  return (
    <div className="import-review" aria-labelledby="import-review-title">
      <div className="review-heading"><div><p className="eyebrow">Safe preview · no changes yet</p><h5 id="import-review-title">Review {preview.fileName}</h5><p>This preview expires in about {Math.max(1, Math.round(preview.expiresInSeconds / 60))} minutes. Project Hope will recheck the same file before saving.</p></div><button className="text-button" disabled={busy} type="button" onClick={onCancel}>Choose another file</button></div>
      <dl className="preview-summary"><div><dt>Rows</dt><dd>{preview.summary.totalRows}</dd></div><div className="good"><dt>Ready to add</dt><dd>{preview.summary.newRecords}</dd></div><div><dt>Existing matches</dt><dd>{preview.summary.exactMatches}</dd></div><div className="warning"><dt>Possible duplicates</dt><dd>{preview.summary.possibleDuplicates}</dd></div><div className="danger"><dt>Needs correction</dt><dd>{preview.summary.invalidRows}</dd></div></dl>
      {preview.warnings.length > 0 && <div className="import-warnings" role="status"><strong>Please note</strong><ul>{preview.warnings.map((warning) => <li key={warning}>{warning}</li>)}</ul></div>}
      <div className="review-table-wrap">
        <table className="review-table">
          <caption className="sr-only">Contact import row review</caption>
          <thead><tr><th scope="col">Row</th><th scope="col">Contact</th><th scope="col">Check</th><th scope="col">What should happen?</th></tr></thead>
          <tbody>{preview.rows.map((row) => <tr key={row.rowNumber} className={`row-${row.status}`}><td>{row.rowNumber}</td><td><strong>{importedName(row)}</strong><small>{[row.values.email, row.values.phone, row.values.external_ref && `Ref ${row.values.external_ref}`].filter(Boolean).join(" · ") || "No email or phone"}</small></td><td><span className={`review-status ${row.status}`}>{statusLabel(row.status)}</span>{row.errors && Object.keys(row.errors).length > 0 && <ul className="row-errors">{Object.entries(row.errors).flatMap(([field, messages]) => messages.map((message) => <li key={`${field}-${message}`}>{field.replaceAll("_", " ")}: {message}</li>))}</ul>}{row.candidates.length > 0 && <small className="match-note">{row.candidates.map((candidate) => `${candidate.displayName} (${candidate.matchReasons.join(", ")})`).join("; ")}</small>}</td><td><label><span className="sr-only">Action for row {row.rowNumber}</span><select aria-label={`Action for row ${row.rowNumber}`} disabled={row.status === "invalid" || busy} value={actions[row.rowNumber] ?? "skip"} onChange={(event) => onAction(row.rowNumber, event.target.value)}>{row.status === "new" && <option value="create">Add as a new contact</option>}<option value="skip">Skip this row</option>{row.candidates.map((candidate) => <option key={candidate.id} value={`update:${candidate.id}`}>Fill missing details on {candidate.displayName}</option>)}</select></label></td></tr>)}</tbody>
        </table>
      </div>
      <div className="review-footer"><div><strong>{selectedCount} {selectedCount === 1 ? "row" : "rows"} selected</strong><small>Existing values are never overwritten. Invalid and skipped rows stay unchanged.</small></div><button aria-busy={busy} className="button primary" disabled={busy || selectedCount === 0} type="button" onClick={onCommit}>{busy ? "Importing safely…" : `Import ${selectedCount} reviewed ${selectedCount === 1 ? "row" : "rows"}`}</button></div>
    </div>
  );
}

function DuplicatePairCard({ pair, disabled, onMerge }: { pair: DuplicatePair; disabled: boolean; onMerge: (primary: string, duplicate: string) => Promise<void> }) {
  const [primary, setPrimary] = useState(pair.first.id);
  const [confirmed, setConfirmed] = useState(false);
  const duplicate = primary === pair.first.id ? pair.second : pair.first;
  const kept = primary === pair.first.id ? pair.first : pair.second;
  const pairName = `${pair.first.displayName} and ${pair.second.displayName}`;
  return (
    <article className="duplicate-card">
      <div className="duplicate-reason"><span className={`confidence ${pair.confidence}`}>{pair.confidence}</span><strong>{pair.matchReasons.join(" · ")}</strong></div>
      <div className="duplicate-contacts"><CandidateCard candidate={pair.first} /><span aria-hidden="true">↔</span><CandidateCard candidate={pair.second} /></div>
      <label className="primary-choice">Keep as the active contact<select aria-label={`Keep as primary for ${pairName}`} disabled={disabled} value={primary} onChange={(event) => { setPrimary(event.target.value); setConfirmed(false); }}><option value={pair.first.id}>{pair.first.displayName}</option><option value={pair.second.id}>{pair.second.displayName}</option></select></label>
      <div className="merge-explanation"><strong>{kept.displayName} stays active.</strong><span>{duplicate.displayName} becomes a preserved source record; blank details and linked history move to the active contact.</span></div>
      <label className="merge-confirm"><input checked={confirmed} disabled={disabled} type="checkbox" onChange={(event) => setConfirmed(event.target.checked)} /><span>I reviewed both records and want to merge this pair.</span></label>
      <button className="button secondary compact" disabled={disabled || !confirmed} type="button" onClick={() => void onMerge(primary, duplicate.id)}>Merge reviewed pair</button>
    </article>
  );
}

function CandidateCard({ candidate }: { candidate: Candidate }) {
  return <div className="candidate-card"><strong>{contactName(candidate)}</strong><small>{candidateSummary(candidate)}</small><span>{candidate.contactType.replaceAll("_", " ")} · {candidate.consentStatus} consent</span></div>;
}
