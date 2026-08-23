import { FormEvent, useEffect, useMemo, useState } from "react";

type Health = {
  status: "ok" | "degraded" | "unknown";
  database: "ok" | "unavailable" | "unknown";
  ai?: { status: "ok" | "degraded" | "disabled" | "unavailable" | "unknown"; runtime?: string };
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

type TeamMember = {
  id: string;
  user: { id: string; email: string; display_name: string };
  role: string;
  active: boolean;
};

type TeamInvitation = {
  id: string;
  email: string;
  role: string;
  status: string;
  effective_status: string;
  delivery_status: string;
  expires_at: string;
  email_sent_at: string | null;
};

type InvitationPreview = {
  organization: { name: string };
  email: string;
  role: string;
  roleLabel: string;
  expiresAt: string;
  existingAccount: boolean;
};

type PasswordResetCredential = { uid: string; token: string };

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

type PilotFormValues = {
  contact_name: string;
  email: string;
  organization_name: string;
  website: string;
  country_or_region: string;
  team_size: string;
  primary_need: string;
  plan_interest: string;
  notes: string;
  consent_to_contact: boolean;
  source: string;
  utm_source: string;
  utm_medium: string;
  utm_campaign: string;
  referrer: string;
  company_website: string;
};

const modules: ModuleDefinition[] = [
  { id: "team", label: "Team & access", description: "Invite staff, assign roles, and review access", endpoint: "members", color: "blue" },
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
  { id: "pwa", label: "Installable web app", description: "A connected workspace that installs from the browser", endpoint: "me", color: "sand" },
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
  const [loginEmail, setLoginEmail] = useState("");
  const [loginPassword, setLoginPassword] = useState("");
  const [loginError, setLoginError] = useState("");
  const [loginBusy, setLoginBusy] = useState(false);
  const [invitationToken, setInvitationToken] = useState("");
  const [passwordReset, setPasswordReset] = useState<PasswordResetCredential | null>(null);
  const [requestPasswordReset, setRequestPasswordReset] = useState(false);
  const [workspaceNotice, setWorkspaceNotice] = useState("");
  const [pilotVerification, setPilotVerification] = useState<"idle" | "checking" | "confirmed" | "error">("idle");
  const [pilotVerificationMessage, setPilotVerificationMessage] = useState("");

  const currentOrganization = useMemo(
    () => session?.organizations.find(({ organization }) => organization.slug === selectedOrganization)?.organization
      ?? session?.organizations[0]?.organization,
    [selectedOrganization, session],
  );
  const currentRole = session?.organizations.find(
    ({ organization }) => organization.slug === currentOrganization?.slug,
  )?.role ?? "";

  useEffect(() => {
    function rememberInstallPrompt(event: Event) {
      event.preventDefault();
      setInstallPrompt(event as InstallPromptEvent);
    }
    window.addEventListener("beforeinstallprompt", rememberInstallPrompt);
    return () => window.removeEventListener("beforeinstallprompt", rememberInstallPrompt);
  }, []);

  useEffect(() => {
    const url = new URL(window.location.href);
    const fragmentParams = new URLSearchParams(url.hash.replace(/^#/, ""));
    const privateCredentialKeys = ["reset_uid", "reset_token", "invite_token", "pilot_token"];
    let removedQueryCredential = false;
    for (const key of privateCredentialKeys) {
      removedQueryCredential = url.searchParams.has(key) || removedQueryCredential;
      url.searchParams.delete(key);
    }
    if (removedQueryCredential) {
      window.history.replaceState({}, "", `${url.pathname}${url.search}${url.hash}`);
    }

    const resetUid = fragmentParams.get("reset_uid");
    const resetToken = fragmentParams.get("reset_token");
    if (resetUid && resetToken) {
      url.searchParams.delete("reset_uid");
      url.searchParams.delete("reset_token");
      url.hash = "";
      window.history.replaceState({}, "", `${url.pathname}${url.search}`);
      setPasswordReset({ uid: resetUid, token: resetToken });
      return;
    }
    const teamToken = fragmentParams.get("invite_token");
    if (teamToken) {
      url.searchParams.delete("invite_token");
      url.hash = "";
      window.history.replaceState({}, "", `${url.pathname}${url.search}`);
      setInvitationToken(teamToken);
      return;
    }

    const token = fragmentParams.get("pilot_token");
    if (!token) return;

    url.searchParams.delete("pilot_token");
    url.hash = "founding-10";
    window.history.replaceState({}, "", `${url.pathname}${url.search}${url.hash}`);
    setPilotVerification("checking");
    request("/api/v1/pilot-applications/verify/", {
      method: "POST",
      body: JSON.stringify({ token }),
    })
      .then((body) => {
        setPilotVerification("confirmed");
        setPilotVerificationMessage(typeof body?.detail === "string" ? body.detail : "Your email is confirmed.");
      })
      .catch((error) => {
        setPilotVerification("error");
        setPilotVerificationMessage(error instanceof Error ? error.message : "Unable to confirm this email.");
      });
  }, []);

  useEffect(() => {
    request("/api/v1/healthz/")
      .then((body: Partial<Health>) => setHealth({
        status: body.status === "ok" || body.status === "degraded" ? body.status : "unknown",
        database: body.database === "ok" || body.database === "unavailable" ? body.database : "unknown",
        ai: body.ai && typeof body.ai === "object"
          ? {
            status: body.ai.status === "ok" || body.ai.status === "degraded" || body.ai.status === "disabled" || body.ai.status === "unavailable" ? body.ai.status : "unknown",
            runtime: body.ai.runtime,
          }
          : { status: "unknown" },
      }))
      .catch(() => setHealth({ status: "degraded", database: "unavailable", ai: { status: "unknown" } }));
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

  async function invitationAccepted(result: {
    detail: string;
    signedIn: boolean;
    organization: Organization;
    user: { email: string };
  }) {
    setWorkspaceNotice(result.detail);
    setInvitationToken("");
    if (result.signedIn) {
      try {
        const nextSession = await request("/api/v1/me/") as Session;
        setSession(nextSession);
        setSelectedOrganization(result.organization.slug);
        setActiveModule("team");
        window.history.replaceState({}, "", `${window.location.pathname}${window.location.search}#workspace`);
        return;
      } catch {
        // A pre-existing account may still need its normal sign-in session.
      }
    }
    setLoginEmail(result.user.email);
    window.history.replaceState({}, "", `${window.location.pathname}${window.location.search}#sign-in`);
  }

  function passwordResetCompleted(email: string, detail: string) {
    setLoginEmail(email);
    setPasswordReset(null);
    setRequestPasswordReset(false);
    setWorkspaceNotice(detail);
    window.history.replaceState({}, "", `${window.location.pathname}${window.location.search}#sign-in`);
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
          {!session && <a href="#founding-10">Founding 10</a>}
          {!session && <a href="#getting-started">Get started</a>}
          <a href="#roadmap">Principles</a>
        </nav>
      </header>

      <main id="main-content">
        {invitationToken && <InvitationAcceptance token={invitationToken} onAccepted={(result) => void invitationAccepted(result)} onCancel={() => setInvitationToken("")} />}
        {!invitationToken && (requestPasswordReset || passwordReset) && <PasswordResetPanel credentials={passwordReset} initialEmail={loginEmail} onCancel={() => { setPasswordReset(null); setRequestPasswordReset(false); }} onCompleted={passwordResetCompleted} />}
        {!invitationToken && !requestPasswordReset && !passwordReset && <>
        {workspaceNotice && <div className="verification-banner" role="status" aria-live="polite"><strong>Access updated</strong><span>{workspaceNotice}</span><button className="text-button" type="button" onClick={() => setWorkspaceNotice("")}>Dismiss</button></div>}
        {pilotVerification !== "idle" && <div className={`verification-banner ${pilotVerification === "error" ? "error" : ""}`} role={pilotVerification === "error" ? "alert" : "status"} aria-live="polite"><strong>{pilotVerification === "checking" ? "Confirming your email…" : pilotVerification === "confirmed" ? "Email confirmed" : "Confirmation problem"}</strong>{pilotVerificationMessage && <span>{pilotVerificationMessage}</span>}</div>}
        <section className="hero" id="overview" aria-labelledby="hero-title">
          <div>
            <p className="eyebrow">Charity-first · human-led</p>
            <h2 id="hero-title">A calm, capable home for community work.</h2>
            <p className="hero-copy">Project Hope keeps charity data under the organization’s control, makes permissions visible, and leaves every consequential decision with a human.</p>
            <div className="hero-actions">
              <a className="button primary" href={session ? "#workspace" : "#founding-10"} onClick={() => session ? setActiveModule("crm") : undefined}>{session ? "Open workspace" : "Apply for Founding 10"}</a>
              {!session && <a className="button secondary" href="#sign-in">Sign in</a>}
              {!session && <a className="button secondary" href="#download">Download the app</a>}
              <a className="button secondary" href="#roadmap">See the guardrails</a>
            </div>
          </div>
          <aside className="health-card" aria-labelledby="health-title">
            <div className="health-heading"><span className={`status-dot ${health.status}`} aria-hidden="true" /><h3 id="health-title">Workspace status</h3></div>
            <p className="health-status" role="status">{health.status === "ok" ? "Ready for work" : health.status === "unknown" ? "Checking services…" : "Needs attention"}</p>
            <dl className="health-details"><div><dt>Core service</dt><dd>{health.status}</dd></div><div><dt>Database</dt><dd>{health.database}</dd></div><div><dt>AI runtime</dt><dd>{health.ai?.status ?? "unknown"}{health.ai?.runtime && health.ai.runtime !== "ollama" ? ` · ${health.ai.runtime}` : ""}</dd></div></dl>
          </aside>
        </section>

        {!session && <FoundingPilotSection />}

        {!session && (
          <section className="section sign-in-section" id="sign-in" aria-labelledby="sign-in-title">
            <div className="section-heading"><div><p className="eyebrow">Organization access</p><h2 id="sign-in-title">Sign in when you’re ready.</h2></div><p>The demo account is for local development only. Production identity belongs behind Keycloak and MFA.</p></div>
            <form className="sign-in-form" onSubmit={login}>
              <label>Email<input type="email" value={loginEmail} onChange={(event) => setLoginEmail(event.target.value)} autoComplete="username" required /></label>
              <label>Password<input type="password" value={loginPassword} onChange={(event) => setLoginPassword(event.target.value)} autoComplete="current-password" required /></label>
              <button aria-busy={loginBusy} className="button primary" disabled={loginBusy} type="submit">{loginBusy ? "Signing in…" : "Sign in"}</button>
              <button className="text-button sign-in-reset" type="button" onClick={() => setRequestPasswordReset(true)}>Forgot password?</button>
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
              <div className="module-content">{activeModule === "overview" ? <WorkspaceOverview onOpen={(id) => setActiveModule(id)} /> : activeModule === "team" ? <TeamPanel organization={currentOrganization} role={currentRole} /> : selectedModule ? <ModulePanel module={selectedModule} organization={currentOrganization} /> : null}</div>
            </div>
          </section>
        )}

        {!session && <section className="section" id="foundation" aria-labelledby="foundation-title"><div className="section-heading"><div><p className="eyebrow">Built for trust</p><h2 id="foundation-title">The foundation is useful on its own.</h2></div><p>AI can be switched off without taking the core platform with it.</p></div><FoundationCards /></section>}

        <section className="section roadmap-section" id="roadmap" aria-labelledby="roadmap-title"><div className="section-heading"><div><p className="eyebrow">Guardrails across the product</p><h2 id="roadmap-title">Small steps, clear proof.</h2></div><p>Every module earns its place by passing safety, accessibility, and operational checks.</p></div><ol className="roadmap-list"><li className="complete"><span>01</span><div><strong>Foundation</strong><p>Identity, tenancy, authorization, audit, and health.</p></div><b>Complete</b></li><li><span>02</span><div><strong>Core operations</strong><p>CRM, volunteers, scheduling, documents, and reporting.</p></div><b>Ready</b></li><li><span>03</span><div><strong>Bounded assistance</strong><p>Email, grants, translation, resources, and reviewable AI.</p></div><b>Human review</b></li><li><span>04</span><div><strong>Expansion</strong><p>PWA, voice, donor cohorts, plugins, and native clients.</p></div><b>Controlled</b></li></ol></section>
        </>}
      </main>
      <footer className="site-footer"><p>Project Hope · free self-hosted core · managed support available</p><p>Human authority over model authority.</p></footer>
    </div>
  );
}

function PasswordResetPanel({
  credentials,
  initialEmail,
  onCancel,
  onCompleted,
}: {
  credentials: PasswordResetCredential | null;
  initialEmail: string;
  onCancel: () => void;
  onCompleted: (email: string, detail: string) => void;
}) {
  const [email, setEmail] = useState(initialEmail);
  const [accountEmail, setAccountEmail] = useState("");
  const [password, setPassword] = useState("");
  const [passwordConfirm, setPasswordConfirm] = useState("");
  const [loading, setLoading] = useState(Boolean(credentials));
  const [busy, setBusy] = useState(false);
  const [sent, setSent] = useState(false);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");

  useEffect(() => {
    if (!credentials) return;
    setLoading(true);
    setError("");
    request("/api/v1/auth/password-reset/inspect/", {
      method: "POST",
      body: JSON.stringify(credentials),
    })
      .then((body: { email: string }) => setAccountEmail(body.email))
      .catch((reason) => setError(reason instanceof Error ? reason.message : "Unable to open this reset link."))
      .finally(() => setLoading(false));
  }, [credentials]);

  async function requestReset(event: FormEvent) {
    event.preventDefault();
    setBusy(true);
    setError("");
    try {
      const result = await request("/api/v1/auth/password-reset/", {
        method: "POST",
        body: JSON.stringify({ email }),
      });
      setMessage(result.detail);
      setSent(true);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Unable to request a password reset.");
    } finally {
      setBusy(false);
    }
  }

  async function confirmReset(event: FormEvent) {
    event.preventDefault();
    setError("");
    if (!credentials) return;
    if (password !== passwordConfirm) {
      setError("The passwords do not match.");
      return;
    }
    setBusy(true);
    try {
      const result = await request("/api/v1/auth/password-reset/confirm/", {
        method: "POST",
        body: JSON.stringify({ ...credentials, password, password_confirm: passwordConfirm }),
      });
      onCompleted(result.email, result.detail);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Unable to change this password.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="invitation-acceptance password-reset-panel" aria-labelledby="password-reset-title">
      <div className="invitation-visual" aria-hidden="true"><span>H</span><p>A secure way back to your community workspace.</p></div>
      <div className="invitation-card">
        <p className="eyebrow">Account recovery</p>
        {credentials ? loading ? <h2 id="password-reset-title">Checking your reset link…</h2> : accountEmail ? (
          <>
            <h2 id="password-reset-title">Choose a new password.</h2>
            <p className="invitation-lede">Resetting <strong>{accountEmail}</strong> will sign out existing sessions and revoke its API sign-in token.</p>
            <form className="invitation-form" onSubmit={confirmReset}>
              <div className="form-grid">
                <label>New password<input autoComplete="new-password" minLength={8} required type="password" value={password} onChange={(event) => setPassword(event.target.value)} /></label>
                <label>Confirm new password<input autoComplete="new-password" minLength={8} required type="password" value={passwordConfirm} onChange={(event) => setPasswordConfirm(event.target.value)} /></label>
              </div>
              <p className="form-hint">Use a long, unique passphrase that you do not use for another service.</p>
              {error && <p className="form-error" role="alert">{error}</p>}
              <div className="form-actions"><button aria-busy={busy} className="button primary" disabled={busy} type="submit">{busy ? "Changing password…" : "Change password"}</button><button className="button secondary" disabled={busy} type="button" onClick={onCancel}>Cancel</button></div>
            </form>
          </>
        ) : (
          <><h2 id="password-reset-title">This reset link cannot be used.</h2><p className="invitation-lede">{error || "It may have expired or already been used."}</p><div className="form-actions"><button className="button primary" type="button" onClick={onCancel}>Back to sign in</button></div></>
        ) : sent ? (
          <><h2 id="password-reset-title">Check your inbox.</h2><p className="invitation-lede">{message}</p><p className="form-hint">For privacy, the response is the same whether or not that address has an active account. The link expires after one hour by default.</p><div className="form-actions"><button className="button secondary" type="button" onClick={onCancel}>Back to sign in</button></div></>
        ) : (
          <>
            <h2 id="password-reset-title">Reset your password.</h2>
            <p className="invitation-lede">Enter your account email. If it matches an active account, Project Hope will send a private one-hour link.</p>
            <form className="invitation-form" onSubmit={requestReset}>
              <label className="standalone-field">Account email<input autoComplete="email" required type="email" value={email} onChange={(event) => setEmail(event.target.value)} /></label>
              {error && <p className="form-error" role="alert">{error}</p>}
              <div className="form-actions"><button aria-busy={busy} className="button primary" disabled={busy} type="submit">{busy ? "Sending…" : "Send reset link"}</button><button className="button secondary" disabled={busy} type="button" onClick={onCancel}>Cancel</button></div>
            </form>
          </>
        )}
      </div>
    </section>
  );
}

function InvitationAcceptance({
  token,
  onAccepted,
  onCancel,
}: {
  token: string;
  onAccepted: (result: {
    detail: string;
    signedIn: boolean;
    organization: Organization;
    user: { email: string };
  }) => void;
  onCancel: () => void;
}) {
  const [preview, setPreview] = useState<InvitationPreview | null>(null);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [firstName, setFirstName] = useState("");
  const [lastName, setLastName] = useState("");
  const [password, setPassword] = useState("");
  const [passwordConfirm, setPasswordConfirm] = useState("");

  useEffect(() => {
    setLoading(true);
    setError("");
    request("/api/v1/invitations/inspect/", {
      method: "POST",
      body: JSON.stringify({ token }),
    })
      .then((body: InvitationPreview) => setPreview(body))
      .catch((reason) => setError(reason instanceof Error ? reason.message : "Unable to open this invitation."))
      .finally(() => setLoading(false));
  }, [token]);

  async function accept(event: FormEvent) {
    event.preventDefault();
    setError("");
    if (!preview?.existingAccount && password !== passwordConfirm) {
      setError("The passwords do not match.");
      return;
    }
    setBusy(true);
    try {
      const result = await request("/api/v1/invitations/accept/", {
        method: "POST",
        body: JSON.stringify({
          token,
          first_name: firstName,
          last_name: lastName,
          password,
          password_confirm: passwordConfirm,
        }),
      });
      onAccepted(result);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Unable to accept this invitation.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="invitation-acceptance" aria-labelledby="invitation-title">
      <div className="invitation-visual" aria-hidden="true"><span>H</span><p>A private invitation to do good work together.</p></div>
      <div className="invitation-card">
        <p className="eyebrow">Secure team invitation</p>
        {loading ? <h2 id="invitation-title">Checking your invitation…</h2> : preview ? (
          <>
            <h2 id="invitation-title">Join {preview.organization.name}.</h2>
            <p className="invitation-lede"><strong>{preview.email}</strong> was invited as <strong>{preview.roleLabel.toLowerCase()}</strong>. This link expires {formatDate(preview.expiresAt)} and works once.</p>
            <form className="invitation-form" onSubmit={accept}>
              {preview.existingAccount ? (
                <div className="invitation-existing"><strong>Your account is ready.</strong><p>Accept now, then sign in with your existing Project Hope password. Your password will not be changed.</p></div>
              ) : (
                <>
                  <div className="form-grid">
                    <label>First name<input autoComplete="given-name" value={firstName} onChange={(event) => setFirstName(event.target.value)} /></label>
                    <label>Last name<input autoComplete="family-name" value={lastName} onChange={(event) => setLastName(event.target.value)} /></label>
                    <label>Password<input autoComplete="new-password" minLength={8} required type="password" value={password} onChange={(event) => setPassword(event.target.value)} /></label>
                    <label>Confirm password<input autoComplete="new-password" minLength={8} required type="password" value={passwordConfirm} onChange={(event) => setPasswordConfirm(event.target.value)} /></label>
                  </div>
                  <p className="form-hint">Use a long, unique passphrase. Project Hope checks it against the server’s password policy before creating the account.</p>
                </>
              )}
              {error && <p className="form-error" role="alert">{error}</p>}
              <div className="form-actions">
                <button aria-busy={busy} className="button primary" disabled={busy} type="submit">{busy ? "Joining…" : preview.existingAccount ? "Accept invitation" : "Create account and join"}</button>
                <button className="button secondary" disabled={busy} type="button" onClick={onCancel}>Not now</button>
              </div>
            </form>
          </>
        ) : (
          <>
            <h2 id="invitation-title">This invitation cannot be used.</h2>
            <p className="invitation-lede">{error || "It may have expired, been revoked, or already been accepted."}</p>
            <button className="button secondary" type="button" onClick={onCancel}>Continue to Project Hope</button>
          </>
        )}
      </div>
    </section>
  );
}

const teamRoles = [
  { value: "owner", label: "Owner" },
  { value: "admin", label: "Administrator" },
  { value: "coordinator", label: "Coordinator" },
  { value: "staff", label: "Staff" },
  { value: "viewer", label: "Viewer" },
];

function TeamPanel({ organization, role }: { organization: Organization; role: string }) {
  const canManage = role === "owner" || role === "admin";
  const [members, setMembers] = useState<TeamMember[]>([]);
  const [invitations, setInvitations] = useState<TeamInvitation[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [inviteEmail, setInviteEmail] = useState("");
  const [inviteRole, setInviteRole] = useState("staff");
  const [busy, setBusy] = useState("");

  async function loadTeam() {
    setLoading(true);
    setError("");
    try {
      const memberData = await request(`/api/v1/organizations/${organization.slug}/members/`) as TeamMember[];
      setMembers(memberData);
      if (canManage) {
        const invitationData = await request(`/api/v1/organizations/${organization.slug}/invitations/`) as TeamInvitation[];
        setInvitations(invitationData);
      } else {
        setInvitations([]);
      }
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Unable to load team access.");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => { void loadTeam(); }, [organization.slug, canManage]);

  async function invite(event: FormEvent) {
    event.preventDefault();
    setBusy("invite");
    setError("");
    setNotice("");
    try {
      const invitation = await request(`/api/v1/organizations/${organization.slug}/invitations/`, {
        method: "POST",
        body: JSON.stringify({ email: inviteEmail, role: inviteRole }),
      }) as TeamInvitation;
      setInviteEmail("");
      setNotice(invitation.delivery_status === "sent" ? `Invitation sent to ${invitation.email}.` : `Invitation saved for ${invitation.email}; email delivery will retry automatically.`);
      await loadTeam();
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Unable to send this invitation.");
    } finally {
      setBusy("");
    }
  }

  async function updateMember(member: TeamMember, changes: { role?: string; active?: boolean }) {
    setBusy(member.id);
    setError("");
    setNotice("");
    try {
      await request(`/api/v1/organizations/${organization.slug}/members/${member.id}/`, {
        method: "PATCH",
        body: JSON.stringify(changes),
      });
      setNotice(`Access updated for ${member.user.display_name}.`);
      await loadTeam();
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Unable to update team access.");
    } finally {
      setBusy("");
    }
  }

  async function resend(invitation: TeamInvitation) {
    setBusy(invitation.id);
    setError("");
    setNotice("");
    try {
      const updated = await request(`/api/v1/organizations/${organization.slug}/invitations/${invitation.id}/resend/`, { method: "POST", body: "{}" }) as TeamInvitation;
      setNotice(updated.delivery_status === "sent" ? `A fresh invitation was sent to ${updated.email}.` : `A fresh invitation was saved for ${updated.email}; delivery will retry automatically.`);
      await loadTeam();
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Unable to resend this invitation.");
    } finally {
      setBusy("");
    }
  }

  async function revoke(invitation: TeamInvitation) {
    if (!window.confirm(`Revoke the invitation for ${invitation.email}?`)) return;
    setBusy(invitation.id);
    setError("");
    setNotice("");
    try {
      await request(`/api/v1/organizations/${organization.slug}/invitations/${invitation.id}/`, { method: "DELETE" });
      setNotice(`Invitation revoked for ${invitation.email}.`);
      await loadTeam();
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Unable to revoke this invitation.");
    } finally {
      setBusy("");
    }
  }

  return (
    <div>
      <div className="module-heading">
        <div><p className="eyebrow">People and permissions</p><h3 className="module-title">Team & access</h3><p className="module-lede">Invite people by email, give each person only the access they need, and revoke pending links at any time.</p></div>
        <span className="module-count">{members.filter((member) => member.active).length} active</span>
      </div>
      {canManage && (
        <form className="team-invite-form" onSubmit={invite}>
          <div><p className="eyebrow">Invite a teammate</p><h4>Send one secure, expiring link.</h4></div>
          <label>Work email<input autoComplete="email" required type="email" value={inviteEmail} onChange={(event) => setInviteEmail(event.target.value)} placeholder="name@charity.org" /></label>
          <label>Role<select value={inviteRole} onChange={(event) => setInviteRole(event.target.value)}>{teamRoles.filter((option) => role === "owner" || option.value !== "owner").map((option) => <option key={option.value} value={option.value}>{option.label}</option>)}</select></label>
          <button aria-busy={busy === "invite"} className="button primary compact" disabled={busy === "invite"} type="submit">{busy === "invite" ? "Sending…" : "Send invitation"}</button>
        </form>
      )}
      {notice && <p className="team-notice" role="status">{notice}</p>}
      {error && <div className="empty-state error-state" role="alert"><strong>Team access needs attention.</strong><p>{error}</p><button className="button secondary compact" type="button" onClick={() => void loadTeam()}>Try again</button></div>}
      {loading ? <p className="loading-state" role="status">Loading team access…</p> : (
        <>
          <section className="team-section" aria-labelledby="members-title">
            <div className="team-section-heading"><div><p className="eyebrow">Current access</p><h4 id="members-title">Team members</h4></div><span>{members.length} total</span></div>
            <div className="team-list">{members.map((member) => {
              const ownerProtectedFromAdmin = role !== "owner" && member.role === "owner";
              return <article className={!member.active ? "inactive" : ""} key={member.id}><div className="avatar" aria-hidden="true">{member.user.display_name.slice(0, 1).toUpperCase()}</div><div className="team-person"><strong>{member.user.display_name}</strong><small>{member.user.email}</small></div>{canManage ? <><label className="role-control"><span className="sr-only">Role for {member.user.display_name}</span><select aria-label={`Role for ${member.user.display_name}`} disabled={busy === member.id || ownerProtectedFromAdmin} value={member.role} onChange={(event) => void updateMember(member, { role: event.target.value })}>{teamRoles.filter((option) => role === "owner" || option.value !== "owner" || member.role === "owner").map((option) => <option key={option.value} value={option.value}>{option.label}</option>)}</select></label><button className="text-button danger" disabled={busy === member.id || ownerProtectedFromAdmin} type="button" onClick={() => { const action = member.active ? "Deactivate" : "Reactivate"; if (window.confirm(`${action} access for ${member.user.display_name}?`)) void updateMember(member, { active: !member.active }); }}>{member.active ? "Deactivate" : "Reactivate"}</button></> : <span className="role-badge">{roleLabel(member.role)}</span>}</article>;
            })}</div>
          </section>
          {canManage && <section className="team-section" aria-labelledby="invitations-title"><div className="team-section-heading"><div><p className="eyebrow">Invitation history</p><h4 id="invitations-title">Invitations</h4></div><span>{invitations.filter((invitation) => invitation.status === "pending").length} pending</span></div>{invitations.length === 0 ? <div className="empty-state"><strong>No invitations yet.</strong><p>Send the first secure link above when your teammate is ready.</p></div> : <div className="invitation-list">{invitations.map((invitation) => <article key={invitation.id}><div><strong>{invitation.email}</strong><small>{roleLabel(invitation.role)} · {invitation.delivery_status === "sent" ? "Email sent" : "Delivery retrying"} · {invitation.effective_status === "expired" ? "Expired" : roleLabel(invitation.effective_status)}</small></div>{invitation.status === "pending" && (role === "owner" || invitation.role !== "owner") && <div className="inline-actions"><button className="text-button" disabled={busy === invitation.id} type="button" onClick={() => void resend(invitation)}>Resend</button><button className="text-button danger" disabled={busy === invitation.id} type="button" onClick={() => void revoke(invitation)}>Revoke</button></div>}</article>)}</div>}</section>}
        </>
      )}
    </div>
  );
}

function roleLabel(value: string) {
  return teamRoles.find((role) => role.value === value)?.label ?? value.charAt(0).toUpperCase() + value.slice(1);
}

function formatDate(value: string) {
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? "soon" : date.toLocaleDateString(undefined, { month: "long", day: "numeric", year: "numeric" });
}

function initialPilotForm(): PilotFormValues {
  const params = new URLSearchParams(window.location.search);
  const utmSource = (params.get("utm_source") ?? "").slice(0, 120);
  const source = utmSource.toLowerCase().includes("linkedin")
    ? "linkedin"
    : document.referrer
      ? "referral"
      : "website";
  return {
    contact_name: "",
    email: "",
    organization_name: "",
    website: "",
    country_or_region: "",
    team_size: "",
    primary_need: "",
    plan_interest: "founding_partner",
    notes: "",
    consent_to_contact: false,
    source,
    utm_source: utmSource,
    utm_medium: (params.get("utm_medium") ?? "").slice(0, 120),
    utm_campaign: (params.get("utm_campaign") ?? "").slice(0, 160),
    referrer: document.referrer.slice(0, 500),
    company_website: "",
  };
}

function FoundingPilotSection() {
  const [values, setValues] = useState<PilotFormValues>(initialPilotForm);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [submitted, setSubmitted] = useState(false);

  function update<K extends keyof PilotFormValues>(name: K, value: PilotFormValues[K]) {
    setValues((current) => ({ ...current, [name]: value }));
  }

  async function submit(event: FormEvent) {
    event.preventDefault();
    setBusy(true);
    setError("");
    try {
      await request("/api/v1/pilot-applications/", {
        method: "POST",
        body: JSON.stringify(values),
      });
      setSubmitted(true);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Unable to send your application.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="section pilot-section" id="founding-10" aria-labelledby="pilot-title">
      <div className="pilot-layout">
        <div className="pilot-pitch">
          <p className="eyebrow">Now accepting applications</p>
          <h2 id="pilot-title">Be one of the Founding 10.</h2>
          <p className="pilot-lede">Ten charities will help shape a simpler way to run community work—and receive a managed workspace with hands-on launch support.</p>
          <div className="pilot-price">
            <span>Founding Partner pilot</span>
            <div><sup>CAD</sup><strong>$149</strong><small>/ month</small></div>
            <p>Charged only after your workspace is live. No setup fee during the pilot. Cancel anytime.</p>
          </div>
          <ul className="pilot-benefits">
            <li><span aria-hidden="true">✓</span><div><strong>We launch it with you</strong><small>Domain, workspace, first admin, and guided onboarding.</small></div></li>
            <li><span aria-hidden="true">✓</span><div><strong>One app, kept current</strong><small>Managed updates, encrypted backups, and human support.</small></div></li>
            <li><span aria-hidden="true">✓</span><div><strong>Your data stays yours</strong><small>Exportable records, clear permissions, and a free self-hosted edition.</small></div></li>
          </ul>
          <p className="pilot-fine-print">Applying is free and does not create a payment obligation. Fit, scope, hosting region, and data terms are confirmed in writing before launch.</p>
        </div>

        <div className="pilot-form-card">
          {submitted ? (
            <div className="pilot-success" role="status" aria-live="polite">
              <span className="success-mark" aria-hidden="true">✓</span>
              <p className="eyebrow">Application received</p>
              <h3>Check your inbox.</h3>
              <p>Open the confirmation link we sent to <strong>{values.email}</strong>. We count only confirmed applications and review every one personally.</p>
              <button className="button secondary compact" type="button" onClick={() => { setValues(initialPilotForm()); setSubmitted(false); }}>Apply for another charity</button>
            </div>
          ) : (
            <form className="pilot-form" onSubmit={submit} aria-label="Founding 10 application">
              <div className="pilot-form-heading"><div><p className="eyebrow">Two-minute application</p><h3>Tell us where help would matter most.</h3></div><span>10 places</span></div>
              <div className="pilot-fields">
                <label>Your name<input autoComplete="name" maxLength={160} required value={values.contact_name} onChange={(event) => update("contact_name", event.target.value)} /></label>
                <label>Work email<input autoComplete="email" maxLength={254} required type="email" value={values.email} onChange={(event) => update("email", event.target.value)} /></label>
                <label>Charity or nonprofit<input autoComplete="organization" maxLength={200} required value={values.organization_name} onChange={(event) => update("organization_name", event.target.value)} /></label>
                <label>Website <small>optional</small><input autoComplete="url" maxLength={500} type="url" placeholder="https://" value={values.website} onChange={(event) => update("website", event.target.value)} /></label>
                <label>Country or region <small>optional</small><input autoComplete="country-name" maxLength={120} value={values.country_or_region} onChange={(event) => update("country_or_region", event.target.value)} /></label>
                <label>Team size<select required value={values.team_size} onChange={(event) => update("team_size", event.target.value)}><option value="" disabled>Select team size</option><option value="1">1 person</option><option value="2-5">2–5 people</option><option value="6-20">6–20 people</option><option value="21-50">21–50 people</option><option value="51+">51+ people</option></select></label>
                <label className="wide-field">What would help most?<select required value={values.primary_need} onChange={(event) => update("primary_need", event.target.value)}><option value="" disabled>Select a priority</option><option value="operations">Operations in one place</option><option value="volunteers">Volunteer coordination</option><option value="grants">Grants and evidence</option><option value="communications">Safer communications</option><option value="impact">Impact and reporting</option><option value="accessibility">Accessibility and translation</option><option value="other">Something else</option></select></label>
              </div>
              <fieldset className="plan-choice"><legend>Which path fits best?</legend><label><input checked={values.plan_interest === "founding_partner"} name="plan" onChange={() => update("plan_interest", "founding_partner")} type="radio" value="founding_partner" /><span><strong>Founding Partner</strong><small>Managed launch and support · CAD $149/month</small></span></label><label><input checked={values.plan_interest === "community"} name="plan" onChange={() => update("plan_interest", "community")} type="radio" value="community" /><span><strong>Community</strong><small>Free software · your team hosts it</small></span></label><label><input checked={values.plan_interest === "network"} name="plan" onChange={() => update("plan_interest", "network")} type="radio" value="network" /><span><strong>Partner Network</strong><small>Multiple charities · tailored rollout</small></span></label></fieldset>
              <label className="notes-field">Anything we should know? <small>optional</small><textarea maxLength={2000} placeholder="The challenge, timing, or outcome you care about…" value={values.notes} onChange={(event) => update("notes", event.target.value)} /></label>
              <div className="honeypot" aria-hidden="true"><label>Company website<input autoComplete="off" tabIndex={-1} value={values.company_website} onChange={(event) => update("company_website", event.target.value)} /></label></div>
              <label className="consent-field"><input checked={values.consent_to_contact} required type="checkbox" onChange={(event) => update("consent_to_contact", event.target.checked)} /><span>I agree that Project Hope may email me about this application. I can withdraw at any time.</span></label>
              <p className="privacy-note">We use these details only to assess and run the pilot. No card is requested. Read the <a href="https://github.com/Fink692/project-hope/blob/main/docs/privacy/pilot-applications.md" target="_blank" rel="noreferrer">pilot privacy notice</a>.</p>
              {error && <p className="form-error" role="alert">{error}</p>}
              <button aria-busy={busy} className="button primary pilot-submit" disabled={busy} type="submit">{busy ? "Sending application…" : "Apply for a Founding 10 place"}</button>
            </form>
          )}
        </div>
      </div>
    </section>
  );
}

function FoundationCards() {
  const cards = ["Identity and organizations", "Tenant safety", "Audit trail", "Bounded AI workflows"];
  return <div className="foundation-grid">{cards.map((label, index) => <article className="foundation-card" key={label}><span className="card-number" aria-hidden="true">0{index + 1}</span><h3>{label}</h3><p>{["Sign-in, organizations, and membership roles", "Every organization view is permission-scoped", "Security events remain append-only", "AI drafts are reviewable, never autonomous"][index]}</p></article>)}</div>;
}

function WorkspaceOverview({ onOpen }: { onOpen: (id: string) => void }) {
  return <div><p className="eyebrow">Your operating surface</p><h3 className="module-title">Choose a module to begin.</h3><p className="module-lede">Everything here stays inside the organization boundary. Start with structured records; add AI only when a reviewable workflow helps.</p><div className="module-grid">{modules.map((module) => <button type="button" className={`module-card ${module.color}`} key={module.id} onClick={() => onOpen(module.id)}><span>{module.label}</span><small>{module.description}</small><b aria-hidden="true">↗</b></button>)}</div></div>;
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
