import { FormEvent, useEffect, useMemo, useState } from "react";

type Health = {
  status: "ok" | "degraded" | "unknown";
  database: "ok" | "unavailable" | "unknown";
};

type Organization = {
  id: string;
  name: string;
  slug: string;
  status: string;
};

type Session = {
  user: { email: string; display_name: string };
  organizations: Array<{ organization: Organization; role: string }>;
};

type ModuleDefinition = {
  id: string;
  label: string;
  description: string;
  endpoint: string;
  color: string;
};

type FormField = {
  name: string;
  label: string;
  type?: "text" | "email" | "url" | "date" | "datetime-local" | "textarea" | "tags" | "select";
  required?: boolean;
  placeholder?: string;
  options?: Array<{ label: string; value: string }>;
};

type RecordMap = Record<string, unknown>;
type InstallPromptEvent = Event & { prompt: () => Promise<void>; userChoice: Promise<{ outcome: "accepted" | "dismissed" }> };

const modules: ModuleDefinition[] = [
  { id: "crm", label: "CRM", description: "People, households, consent, and relationships", endpoint: "contacts", color: "sage" },
  { id: "volunteers", label: "Volunteers", description: "Applications, skills, availability, and onboarding", endpoint: "volunteer-applications", color: "blue" },
  { id: "scheduling", label: "Scheduling", description: "Appointments, shifts, resources, and reminders", endpoint: "schedules", color: "sand" },
  { id: "documents", label: "Documents", description: "Permission-aware files, passages, and citations", endpoint: "documents", color: "coral" },
  { id: "email", label: "Email assistant", description: "Triage and drafts with explicit send approval", endpoint: "email-drafts", color: "sage" },
  { id: "analytics", label: "Analytics", description: "Owned metrics, snapshots, and accessible reports", endpoint: "metrics", color: "blue" },
  { id: "grants", label: "Grant workspace", description: "Questions, evidence, budgets, and review", endpoint: "grants", color: "sand" },
  { id: "resources", label: "Resource directory", description: "Verified local services with freshness status", endpoint: "resources", color: "coral" },
  { id: "translation", label: "Translation", description: "Reviewable segments and translation memory", endpoint: "translations", color: "sage" },
  { id: "accessibility", label: "Accessibility", description: "Plain language, OCR, audio, and accessible views", endpoint: "accessibility-transforms", color: "blue" },
  { id: "voice", label: "Phone workspace", description: "Bounded intents, consent, callback, and escalation", endpoint: "calls", color: "sand" },
  { id: "donors", label: "Donor insights", description: "Descriptive cohorts and transparent reason codes", endpoint: "donor-snapshots", color: "coral" },
  { id: "plugins", label: "Plugin catalogue", description: "Administrator-controlled, capability-scoped packages", endpoint: "plugins", color: "sage" },
  { id: "api", label: "Public API", description: "Tenant-bound clients and explicit scopes", endpoint: "api-clients", color: "blue" },
  { id: "pwa", label: "PWA / offline", description: "Installable, low-bandwidth workspace shell", endpoint: "me", color: "sand" },
  { id: "ai", label: "AI workflows", description: "Bounded operations with review and provenance", endpoint: "workflows", color: "coral" },
];

const moduleForms: Record<string, FormField[]> = {
  crm: [
    { name: "contact_type", label: "Record type", type: "select", options: [{ label: "Person", value: "person" }, { label: "Organization", value: "organization" }, { label: "Service user", value: "service_user" }, { label: "Donor", value: "donor" }, { label: "Volunteer", value: "volunteer" }] },
    { name: "first_name", label: "First name" },
    { name: "last_name", label: "Last name" },
    { name: "email", label: "Email", type: "email" },
    { name: "phone", label: "Phone" },
    { name: "consent_status", label: "Consent", type: "select", options: [{ label: "Unknown", value: "unknown" }, { label: "Granted", value: "granted" }, { label: "Withdrawn", value: "withdrawn" }] },
    { name: "notes", label: "Notes", type: "textarea" },
  ],
  volunteers: [
    { name: "applicant_name", label: "Applicant name", required: true },
    { name: "email", label: "Email", type: "email", required: true },
    { name: "phone", label: "Phone" },
    { name: "skills", label: "Skills", type: "tags", placeholder: "First aid, reception, driving" },
    { name: "interests", label: "Interests", type: "tags", placeholder: "Food support, youth work" },
    { name: "notes", label: "Notes", type: "textarea" },
  ],
  scheduling: [
    { name: "title", label: "Event title", required: true },
    { name: "event_type", label: "Event type", type: "select", options: [{ label: "Appointment", value: "appointment" }, { label: "Volunteer shift", value: "shift" }, { label: "Meeting", value: "meeting" }, { label: "Closure", value: "closure" }] },
    { name: "starts_at", label: "Starts", type: "datetime-local", required: true },
    { name: "ends_at", label: "Ends", type: "datetime-local", required: true },
    { name: "location", label: "Location" },
    { name: "notes", label: "Notes", type: "textarea" },
  ],
  resources: [
    { name: "name", label: "Service name", required: true },
    { name: "category", label: "Category", required: true, placeholder: "Food, housing, counselling" },
    { name: "description", label: "Description", type: "textarea", required: true },
    { name: "languages", label: "Languages", type: "tags", placeholder: "English, French" },
    { name: "accessibility", label: "Accessibility", type: "tags", placeholder: "Wheelchair access, ASL" },
    { name: "address", label: "Address", type: "textarea" },
    { name: "source_url", label: "Source URL", type: "url" },
  ],
  grants: [
    { name: "name", label: "Grant name", required: true },
    { name: "funder", label: "Funder", required: true },
    { name: "deadline", label: "Deadline", type: "date" },
    { name: "organizational_profile", label: "Organization profile", type: "textarea" },
  ],
};

function readCookie(name: string) {
  return document.cookie
    .split("; ")
    .find((row) => row.startsWith(`${name}=`))
    ?.split("=")[1];
}

async function request(path: string, init: RequestInit = {}) {
  const headers = new Headers(init.headers);
  if (init.body && !headers.has("Content-Type")) headers.set("Content-Type", "application/json");
  const csrf = readCookie("csrftoken");
  if (csrf) headers.set("X-CSRFToken", csrf);
  const response = await fetch(path, { ...init, headers, credentials: "include" });
  const body = await response.json().catch(() => ({}));
  if (!response.ok) {
    const detail = typeof body?.detail === "string" ? body.detail : "";
    const fieldErrors = body && typeof body === "object"
      ? Object.entries(body as Record<string, unknown>)
        .filter(([key]) => key !== "detail")
        .map(([key, value]) => key + ": " + (Array.isArray(value) ? value.join(", ") : String(value)))
        .join(" · ")
      : "";
    throw new Error(detail || fieldErrors || "Request failed (" + response.status + ")");
  }
  return body;
}

function App() {
  const [health, setHealth] = useState<Health>({ status: "unknown", database: "unknown" });
  const [session, setSession] = useState<Session | null>(null);
  const [installPrompt, setInstallPrompt] = useState<InstallPromptEvent | null>(null);
  const [activeModule, setActiveModule] = useState("overview");
  const [selectedOrganization, setSelectedOrganization] = useState("");
  const [loginEmail, setLoginEmail] = useState("demo@example.org");
  const [loginPassword, setLoginPassword] = useState("");
  const [loginError, setLoginError] = useState("");
  const [loginBusy, setLoginBusy] = useState(false);

  const currentOrganization = useMemo(
    () => session?.organizations.find(({ organization }) => organization.slug === selectedOrganization)?.organization
      ?? session?.organizations[0]?.organization,
    [selectedOrganization, session],
  );

  useEffect(() => {
    function rememberInstallPrompt(event: Event) {
      event.preventDefault();
      setInstallPrompt(event as InstallPromptEvent);
    }
    window.addEventListener("beforeinstallprompt", rememberInstallPrompt);
    return () => window.removeEventListener("beforeinstallprompt", rememberInstallPrompt);
  }, []);

  useEffect(() => {
    request("/api/v1/healthz/")
      .then((body: Partial<Health>) => setHealth({
        status: body.status === "ok" || body.status === "degraded" ? body.status : "unknown",
        database: body.database === "ok" || body.database === "unavailable" ? body.database : "unknown",
      }))
      .catch(() => setHealth({ status: "degraded", database: "unavailable" }));
    request("/api/v1/me/").then((body: Session) => {
      if (Array.isArray(body?.organizations)) setSession(body);
    }).catch(() => undefined);
  }, []);

  useEffect(() => {
    if (session && !selectedOrganization) setSelectedOrganization(session.organizations[0]?.organization.slug ?? "");
  }, [selectedOrganization, session]);

  async function login(event: FormEvent) {
    event.preventDefault();
    setLoginError("");
    setLoginBusy(true);
    try {
      await request("/api/v1/auth/csrf/");
      await request("/api/v1/auth/login/", { method: "POST", body: JSON.stringify({ email: loginEmail, password: loginPassword }) });
      setSession(await request("/api/v1/me/"));
      setLoginPassword("");
    } catch (error) {
      setLoginError(error instanceof Error ? error.message : "Unable to sign in.");
    } finally {
      setLoginBusy(false);
    }
  }

  async function logout() {
    try { await request("/api/v1/auth/logout/", { method: "POST", body: "{}" }); } finally { setSession(null); }
  }

  async function installApp() {
    if (!installPrompt) return;
    await installPrompt.prompt();
    await installPrompt.userChoice;
    setInstallPrompt(null);
  }

  const selectedModule = modules.find((module) => module.id === activeModule);

  return (
    <div className="app-shell">
      <a className="skip-link" href="#main-content">Skip to main content</a>
      <header className="site-header">
        <div className="brand-block">
          <span className="brand-mark" aria-hidden="true">H</span>
          <div><p className="eyebrow">Charity operations platform</p><h1>Project Hope</h1></div>
        </div>
        <nav aria-label="Primary navigation">
          <a aria-current={activeModule === "overview" ? "page" : undefined} className={activeModule === "overview" ? "active" : ""} href="#overview" onClick={() => setActiveModule("overview")}>Overview</a>
          <a href="#workspace" onClick={() => setActiveModule(session ? "crm" : "overview")}>Workspace</a>
          {!session && <a href="#getting-started">Get started</a>}
          <a href="#roadmap">Principles</a>
        </nav>
      </header>

      <main id="main-content">
        <section className="hero" id="overview" aria-labelledby="hero-title">
          <div>
            <p className="eyebrow">Local-first · human-led</p>
            <h2 id="hero-title">A calm, capable home for community work.</h2>
            <p className="hero-copy">Project Hope keeps charity data under the organization’s control, makes permissions visible, and leaves every consequential decision with a human.</p>
            <div className="hero-actions">
              <a className="button primary" href={session ? "#workspace" : "#sign-in"} onClick={() => session ? setActiveModule("crm") : undefined}>{session ? "Open workspace" : "Sign in to workspace"}</a>
              {!session && <a className="button secondary" href="#download">Install the app</a>}
              <a className="button secondary" href="#roadmap">See the guardrails</a>
            </div>
          </div>
          <aside className="health-card" aria-labelledby="health-title">
            <div className="health-heading"><span className={`status-dot ${health.status}`} aria-hidden="true" /><h3 id="health-title">Local system status</h3></div>
            <p className="health-status" role="status">{health.status === "ok" ? "Ready for local work" : health.status === "unknown" ? "Checking services…" : "Needs attention"}</p>
            <dl className="health-details"><div><dt>Core service</dt><dd>{health.status}</dd></div><div><dt>Database</dt><dd>{health.database}</dd></div></dl>
          </aside>
        </section>

        {!session && (
          <section className="section sign-in-section" id="sign-in" aria-labelledby="sign-in-title">
            <div className="section-heading"><div><p className="eyebrow">Organization access</p><h2 id="sign-in-title">Sign in when you’re ready.</h2></div><p>The demo account is for local development only. Production identity belongs behind Keycloak and MFA.</p></div>
            <form className="sign-in-form" onSubmit={login}>
              <label>Email<input type="email" value={loginEmail} onChange={(event) => setLoginEmail(event.target.value)} autoComplete="username" required /></label>
              <label>Password<input type="password" value={loginPassword} onChange={(event) => setLoginPassword(event.target.value)} autoComplete="current-password" required /></label>
              <button aria-busy={loginBusy} className="button primary" disabled={loginBusy} type="submit">{loginBusy ? "Signing in…" : "Sign in"}</button>
              {loginError && <p className="form-error" role="alert">{loginError}</p>}
            </form>
            <aside className="onboarding-card" aria-labelledby="onboarding-title">
              <div><p className="eyebrow">New to Project Hope?</p><h3 id="onboarding-title">You should not need to be technical to get started.</h3><p>A coordinator can run one guided setup command, open this page, and invite the team. The plain-language guide explains every step.</p></div>
              <ol className="onboarding-steps"><li><span>01</span><div><strong>Set up once</strong><small>Use the guided helper on the computer that will host the workspace.</small></div></li><li><span>02</span><div><strong>Open the workspace</strong><small>Project Hope checks its services and opens the browser for you.</small></div></li><li><span>03</span><div><strong>Start with one task</strong><small>Choose CRM, Volunteers, or Scheduling. Add more when your team is ready.</small></div></li></ol>
              <a className="button secondary compact" href="https://github.com/Fink692/project-hope/blob/main/docs/GETTING_STARTED_FOR_CHARITIES.md" target="_blank" rel="noreferrer">Open the plain-language guide</a>
            </aside>
          </section>
        )}

        {!session && <section className="section download-section" id="download" aria-labelledby="download-title"><div className="section-heading"><div><p className="eyebrow">One workspace, every device</p><h2 id="download-title">Install Project Hope like an app.</h2></div><p>Your charity gets one hosted workspace. Staff can install it on desktop, use the mobile app, and see the same organization data everywhere.</p></div><div className="download-grid"><article className="download-card featured"><span className="card-number" aria-hidden="true">01</span><h3>Desktop installer</h3><p>Download the Windows, macOS, or Linux installer prepared for your workspace. It opens like a normal app and updates with releases.</p><div className="card-actions"><a className="button primary compact" href="https://github.com/Fink692/project-hope/releases/latest" target="_blank" rel="noreferrer">Download installer</a>{installPrompt ? <button className="button secondary compact" type="button" onClick={() => void installApp()}>Install from browser</button> : <small>ChromeOS and browser users can choose “Install Project Hope” from the browser menu.</small>}</div></article><article className="download-card"><span className="card-number" aria-hidden="true">02</span><h3>iPhone and Android</h3><p>The Expo mobile client uses the same secure sign-in and hosted workspace for field work, schedules, volunteers, and tasks.</p><small>App Store builds are prepared by the organization’s setup partner with its own signing accounts.</small></article><article className="download-card"><span className="card-number" aria-hidden="true">03</span><h3>Everything connected</h3><p>No duplicate databases, file transfers, or per-device setup. One organization boundary, one login, one source of truth.</p><a className="button secondary compact" href="https://github.com/Fink692/project-hope/blob/main/docs/DISTRIBUTION_FOR_CHARITIES.md" target="_blank" rel="noreferrer">See how it works</a></article></div></section>}

        {session && currentOrganization && (
          <section className="section workspace" id="workspace" aria-labelledby="workspace-title">
            <div className="workspace-header">
              <div><p className="eyebrow">{session.user.display_name}</p><h2 id="workspace-title">{currentOrganization.name}</h2><p className="workspace-role">Signed in as {session.organizations.find(({ organization }) => organization.slug === currentOrganization.slug)?.role}</p></div>
              <div className="workspace-controls"><label className="organization-select">Organization<select value={currentOrganization.slug} onChange={(event) => setSelectedOrganization(event.target.value)}>{session.organizations.map(({ organization }) => <option key={organization.slug} value={organization.slug}>{organization.name}</option>)}</select></label><button className="text-button" type="button" onClick={logout}>Sign out</button></div>
            </div>
            <div className="workspace-layout">
              <nav className="module-nav" aria-label="Workspace modules">
                <button aria-current={activeModule === "overview" ? "page" : undefined} className={activeModule === "overview" ? "selected" : ""} type="button" onClick={() => setActiveModule("overview")}>Workspace overview</button>
                {modules.map((module) => <button aria-current={activeModule === module.id ? "page" : undefined} className={activeModule === module.id ? "selected" : ""} type="button" key={module.id} onClick={() => setActiveModule(module.id)}>{module.label}</button>)}
              </nav>
              <div className="module-content">{activeModule === "overview" ? <WorkspaceOverview onOpen={(id) => setActiveModule(id)} /> : selectedModule ? <ModulePanel module={selectedModule} organization={currentOrganization} /> : null}</div>
            </div>
          </section>
        )}

        {!session && <section className="section" id="foundation" aria-labelledby="foundation-title"><div className="section-heading"><div><p className="eyebrow">Built for trust</p><h2 id="foundation-title">The foundation is useful on its own.</h2></div><p>AI can be switched off without taking the core platform with it.</p></div><FoundationCards /></section>}

        <section className="section roadmap-section" id="roadmap" aria-labelledby="roadmap-title"><div className="section-heading"><div><p className="eyebrow">Guardrails across the product</p><h2 id="roadmap-title">Small steps, clear proof.</h2></div><p>Every module earns its place by passing safety, accessibility, and operational checks.</p></div><ol className="roadmap-list"><li className="complete"><span>01</span><div><strong>Foundation</strong><p>Identity, tenancy, authorization, audit, and health.</p></div><b>Complete</b></li><li><span>02</span><div><strong>Core operations</strong><p>CRM, volunteers, scheduling, documents, and reporting.</p></div><b>Ready</b></li><li><span>03</span><div><strong>Bounded assistance</strong><p>Email, grants, translation, resources, and reviewable AI.</p></div><b>Human review</b></li><li><span>04</span><div><strong>Expansion</strong><p>PWA, voice, donor cohorts, plugins, and native clients.</p></div><b>Controlled</b></li></ol></section>
      </main>
      <footer className="site-footer"><p>Project Hope · self-hosted by design</p><p>Human authority over model authority.</p></footer>
    </div>
  );
}

function FoundationCards() {
  const cards = ["Identity and organizations", "Tenant safety", "Audit trail", "Bounded AI workflows"];
  return <div className="foundation-grid">{cards.map((label, index) => <article className="foundation-card" key={label}><span className="card-number" aria-hidden="true">0{index + 1}</span><h3>{label}</h3><p>{["Sign-in, organizations, and membership roles", "Every organization view is permission-scoped", "Security events remain append-only", "AI drafts are reviewable, never autonomous"][index]}</p></article>)}</div>;
}

function WorkspaceOverview({ onOpen }: { onOpen: (id: string) => void }) {
  return <div><p className="eyebrow">Your operating surface</p><h3 className="module-title">Choose a module to begin.</h3><p className="module-lede">Everything here stays inside the organization boundary. Start with structured records; add AI only when a reviewable workflow helps.</p><div className="module-grid">{modules.map((module) => <button type="button" className={`module-card ${module.color}`} key={module.id} onClick={() => onOpen(module.id)}><span>{module.label}</span><small>{module.description}</small><b aria-hidden="true">↗</b></button>)}</div><OfflineDraftPad /></div>;
}

function OfflineDraftPad() {
  const [draft, setDraft] = useState(() => {
    try {
      return localStorage.getItem("project-hope-offline-draft") ?? "";
    } catch {
      return "";
    }
  });
  const [saved, setSaved] = useState(false);
  const [storageError, setStorageError] = useState(false);
  function save() {
    try {
      localStorage.setItem("project-hope-offline-draft", draft.slice(0, 4000));
      setSaved(true);
      setStorageError(false);
    } catch {
      setSaved(false);
      setStorageError(true);
    }
  }
  return <aside className="offline-pad" aria-labelledby="offline-pad-title"><div><p className="eyebrow">Offline-safe scratchpad</p><h4 id="offline-pad-title">Capture a bounded note.</h4><p>Stored only in this browser until you choose where to move it.</p></div><textarea maxLength={4000} value={draft} onChange={(event) => { setDraft(event.target.value); setSaved(false); setStorageError(false); }} placeholder="A reminder for your next connected session…" aria-label="Offline draft note" /><div className="offline-pad-footer"><button className="button secondary" type="button" onClick={save}>Save on this device</button><span role="status">{saved ? "Saved locally" : storageError ? "Browser storage unavailable" : "Not saved"}</span></div></aside>;
}

function ModulePanel({ module, organization }: { module: ModuleDefinition; organization: Organization }) {
  const [data, setData] = useState<unknown>(null);
  const [error, setError] = useState("");
  const [query, setQuery] = useState("");
  const [submittedQuery, setSubmittedQuery] = useState("");
  const [showCreate, setShowCreate] = useState(false);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const fields = moduleForms[module.id] ?? [];

  async function load(nextQuery = submittedQuery) {
    setData(null);
    setError("");
    try {
      const suffix = nextQuery ? "?q=" + encodeURIComponent(nextQuery) : "";
      setSubmittedQuery(nextQuery);
      setData(await request("/api/v1/organizations/" + organization.slug + "/" + module.endpoint + "/" + suffix));
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Unable to load module.");
    }
  }

  useEffect(() => { void load(""); }, [module.endpoint, organization.slug]);

  async function refresh() {
    setIsRefreshing(true);
    await load();
    setIsRefreshing(false);
  }

  const items = Array.isArray(data) ? data : typeof data === "object" && data !== null ? Object.values(data as Record<string, unknown>).find(Array.isArray) ?? [] : [];
  return (
    <div>
      <div className="module-heading">
        <div><p className="eyebrow">Workspace module</p><h3 className="module-title">{module.label}</h3><p className="module-lede">{module.description}</p></div>
        <span className="module-count" aria-label={items.length + " records"}>{items.length} records</span>
      </div>
      <div className="module-toolbar" role="search">
        <label className="search-field"><span className="sr-only">Search {module.label}</span><input value={query} onChange={(event) => setQuery(event.target.value)} onKeyDown={(event) => { if (event.key === "Enter") void load(query.trim()); }} placeholder={"Search " + module.label.toLowerCase()} type="search" /></label>
        <button className="button secondary compact" type="button" onClick={() => void load(query.trim())}>Search</button>
        <button className="button secondary compact" type="button" disabled={isRefreshing} onClick={() => void refresh()}>{isRefreshing ? "Refreshing…" : "Refresh"}</button>
        {fields.length > 0 && <button className="button primary compact" type="button" onClick={() => setShowCreate((value) => !value)}>{showCreate ? "Close form" : "New record"}</button>}
      </div>
      {showCreate && fields.length > 0 && <CreateRecordForm fields={fields} endpoint={module.endpoint} organization={organization} onCreated={() => { setShowCreate(false); void load(); }} />}
      {error ? <div className="empty-state error-state" role="alert"><strong>Could not load this module.</strong><p>{error}</p><button className="button secondary compact" type="button" onClick={() => void load()}>Try again</button><small>Confirm your membership and local API health status.</small></div> : data === null ? <p className="loading-state" role="status">Loading {module.label}…</p> : items.length === 0 ? <div className="empty-state"><strong>{submittedQuery ? "No matching records." : "No records yet."}</strong><p>{submittedQuery ? "Try a different search term." : "This module is ready for its first organization-controlled record."}</p></div> : <div className="record-list">{items.slice(0, 100).map((item, index) => <article key={recordKey(item, index)}><strong>{recordTitle(item, index)}</strong><small>{recordSummary(item)}</small></article>)}</div>}
    </div>
  );
}

function CreateRecordForm({ fields, endpoint, organization, onCreated }: { fields: FormField[]; endpoint: string; organization: Organization; onCreated: () => void }) {
  const [values, setValues] = useState<Record<string, string>>(() => Object.fromEntries(fields.map((field) => [field.name, field.type === "select" ? field.options?.[0]?.value ?? "" : ""])));
  const [error, setError] = useState("");
  const [saving, setSaving] = useState(false);

  function update(name: string, value: string) {
    setValues((current) => ({ ...current, [name]: value }));
  }

  async function submit(event: FormEvent) {
    event.preventDefault();
    setError("");
    setSaving(true);
    const payload: Record<string, unknown> = { ...values };
    for (const field of fields) {
      if (field.type === "tags") payload[field.name] = values[field.name].split(",").map((item) => item.trim()).filter(Boolean);
      if (field.type === "datetime-local" && values[field.name]) payload[field.name] = new Date(values[field.name]).toISOString();
      if (!values[field.name] && !field.required) delete payload[field.name];
    }
    try {
      await request("/api/v1/organizations/" + organization.slug + "/" + endpoint + "/", { method: "POST", body: JSON.stringify(payload) });
      onCreated();
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Unable to create this record.");
    } finally {
      setSaving(false);
    }
  }

  return <form className="record-form" onSubmit={submit} aria-label={"Create " + endpoint + " record"}><div className="form-grid">{fields.map((field) => <label key={field.name}>{field.label}{field.type === "textarea" ? <textarea value={values[field.name]} onChange={(event) => update(field.name, event.target.value)} placeholder={field.placeholder} required={field.required} /> : field.type === "select" ? <select value={values[field.name]} onChange={(event) => update(field.name, event.target.value)} required={field.required}>{field.options?.map((option) => <option key={option.value} value={option.value}>{option.label}</option>)}</select> : <input type={field.type === "tags" ? "text" : field.type ?? "text"} value={values[field.name]} onChange={(event) => update(field.name, event.target.value)} placeholder={field.placeholder} required={field.required} />}</label>)}</div>{error && <p className="form-error" role="alert">{error}</p>}<div className="form-actions"><button className="button primary compact" disabled={saving} type="submit">{saving ? "Saving…" : "Save record"}</button><span className="form-hint">Saved inside {organization.name} only.</span></div></form>;
}

function recordKey(item: unknown, index: number) { if (typeof item !== "object" || item === null) return String(index); const record = item as RecordMap; return String(record.id ?? record.external_id ?? index); }
function recordTitle(item: unknown, index: number) { if (typeof item !== "object" || item === null) return "Record " + (index + 1); const record = item as RecordMap; return String(record.display_name ?? record.name ?? record.title ?? record.subject ?? record.applicant_name ?? record.key ?? "Record " + (index + 1)); }
function recordSummary(item: unknown) { if (typeof item !== "object" || item === null) return ""; const record = item as RecordMap; return String(record.description ?? record.status ?? record.email ?? record.definition ?? record.phone ?? "Organization-controlled record"); }

export default App;
