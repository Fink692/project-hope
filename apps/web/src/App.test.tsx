import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import axe from "axe-core";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import App from "./App";

describe("Project Hope web shell", () => {
  afterEach(() => cleanup());

  beforeEach(() => {
    window.history.replaceState({}, "", "/");
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(
        new Response(JSON.stringify({ status: "ok", database: "ok" }), {
          status: 200,
          headers: { "Content-Type": "application/json" },
        }),
      ),
    );
  });

  it("provides accessible navigation and a healthy service status", async () => {
    render(<App />);

    expect(screen.getByRole("link", { name: "Skip to main content" })).toBeInTheDocument();
    expect(screen.getByRole("navigation", { name: "Primary navigation" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Get started" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Download installer" })).toHaveAttribute("href", "https://github.com/Fink692/project-hope/releases/latest");
    expect(screen.getByRole("heading", { name: "Be one of the Founding 10." })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "You should not need to be technical to get started." })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Install Project Hope like an app." })).toBeInTheDocument();
    expect(screen.getByText("Community preview")).toBeInTheDocument();
    expect(screen.getByText("Self-hosted source · licensing terms pending")).toBeInTheDocument();
    expect(screen.getByRole("main")).toHaveAttribute("id", "main-content");
    expect(await screen.findByRole("status")).toHaveTextContent("Ready for work");
  });

  it("has no automated WCAG A or AA violations on the public journey", async () => {
    const { container } = render(<App />);
    const results = await axe.run(container, {
      runOnly: {
        type: "tag",
        values: ["wcag2a", "wcag2aa", "wcag21a", "wcag21aa", "wcag22aa"],
      },
      rules: { "color-contrast": { enabled: false } },
    });

    expect(
      results.violations.map(({ id, impact, nodes }) => ({
        id,
        impact,
        targets: nodes.map((node) => node.target),
      })),
    ).toEqual([]);
  });

  it("signs in and creates a tenant-scoped contact from the workspace", async () => {
    let loggedIn = false;
    let contacts: unknown[] = [];
    const fetchMock = vi.fn((input: RequestInfo | URL, init?: RequestInit) => {
      const path = String(input);
      if (path.endsWith("/healthz/")) return Promise.resolve(new Response(JSON.stringify({ status: "ok", database: "ok" }), { status: 200 }));
      if (path.endsWith("/auth/csrf/")) return Promise.resolve(new Response(JSON.stringify({ csrfTokenAvailable: true }), { status: 200 }));
      if (path.endsWith("/auth/login/")) {
        loggedIn = true;
        return Promise.resolve(new Response(JSON.stringify({ user: { email: "demo@example.org", display_name: "Demo User" } }), { status: 200 }));
      }
      if (path.endsWith("/me/")) {
        return Promise.resolve(loggedIn
          ? new Response(JSON.stringify({ user: { email: "demo@example.org", display_name: "Demo User" }, organizations: [{ organization: { id: "1", name: "Hope Demo", slug: "hope-demo", status: "active" }, role: "owner" }] }), { status: 200 })
          : new Response(JSON.stringify({ detail: "Authentication credentials were not provided." }), { status: 401 }));
      }
      if (path.includes("/contacts/") && init?.method === "POST") {
        contacts = [{ id: "contact-1", display_name: "Amina Hope", email: "amina@example.org" }];
        return Promise.resolve(new Response(JSON.stringify(contacts[0]), { status: 201 }));
      }
      if (path.includes("/contacts/")) return Promise.resolve(new Response(JSON.stringify(contacts), { status: 200 }));
      return Promise.resolve(new Response("{}", { status: 200 }));
    });
    vi.stubGlobal("fetch", fetchMock);

    render(<App />);
    await screen.findByRole("button", { name: "Sign in" });
    fireEvent.change(screen.getByLabelText("Email"), { target: { value: "demo@example.org" } });
    fireEvent.change(screen.getByLabelText("Password"), { target: { value: "password" } });
    fireEvent.click(screen.getByRole("button", { name: "Sign in" }));

    await screen.findByRole("button", { name: "CRM" });
    fireEvent.click(screen.getAllByRole("button", { name: "CRM" })[0]);
    await screen.findByRole("button", { name: "New record" });
    fireEvent.click(screen.getByRole("button", { name: "New record" }));
    fireEvent.change(screen.getByLabelText("First name"), { target: { value: "Amina" } });
    fireEvent.change(screen.getByLabelText("Last name"), { target: { value: "Hope" } });
    fireEvent.click(screen.getByRole("button", { name: "Save record" }));

    expect(await screen.findByText("Amina Hope")).toBeInTheDocument();
    expect(fetchMock.mock.calls.some(([, requestInit]) => requestInit?.method === "POST")).toBe(true);
  });

  it("captures a consented Founding 10 application with campaign attribution", async () => {
    window.history.replaceState({}, "", "/?utm_source=linkedin&utm_medium=social&utm_campaign=founding-10");
    let submittedPayload: Record<string, unknown> | undefined;
    const fetchMock = vi.fn((input: RequestInfo | URL, init?: RequestInit) => {
      const path = String(input);
      if (path.endsWith("/healthz/")) return Promise.resolve(new Response(JSON.stringify({ status: "ok", database: "ok" }), { status: 200 }));
      if (path.endsWith("/me/")) return Promise.resolve(new Response(JSON.stringify({ detail: "Authentication credentials were not provided." }), { status: 401 }));
      if (path.endsWith("/pilot-applications/") && init?.method === "POST") {
        submittedPayload = JSON.parse(String(init.body));
        return Promise.resolve(new Response(JSON.stringify({ detail: "Application received. Check your email to confirm your request." }), { status: 202 }));
      }
      return Promise.resolve(new Response("{}", { status: 200 }));
    });
    vi.stubGlobal("fetch", fetchMock);

    render(<App />);
    fireEvent.change(screen.getByLabelText("Your name"), { target: { value: "Amina Hope" } });
    fireEvent.change(screen.getByLabelText("Work email"), { target: { value: "amina@example.org" } });
    fireEvent.change(screen.getByLabelText("Charity or nonprofit"), { target: { value: "North Star Centre" } });
    fireEvent.change(screen.getByLabelText("Team size"), { target: { value: "6-20" } });
    fireEvent.change(screen.getByLabelText("What would help most?"), { target: { value: "volunteers" } });
    fireEvent.click(screen.getByRole("checkbox", { name: /I agree that Project Hope may email me/i }));
    fireEvent.click(screen.getByRole("button", { name: "Apply for a Founding 10 place" }));

    expect(await screen.findByRole("heading", { name: "Check your inbox." })).toBeInTheDocument();
    expect(submittedPayload).toMatchObject({
      email: "amina@example.org",
      organization_name: "North Star Centre",
      plan_interest: "founding_partner",
      consent_to_contact: true,
      source: "linkedin",
      utm_source: "linkedin",
      utm_medium: "social",
      utm_campaign: "founding-10",
    });
  });

  it("confirms an emailed application and removes the private fragment token", async () => {
    window.history.replaceState({}, "", "/#pilot_token=signed-token");
    const fetchMock = vi.fn((input: RequestInfo | URL, init?: RequestInit) => {
      const path = String(input);
      if (path.endsWith("/healthz/")) return Promise.resolve(new Response(JSON.stringify({ status: "ok", database: "ok" }), { status: 200 }));
      if (path.endsWith("/me/")) return Promise.resolve(new Response("{}", { status: 401 }));
      if (path.endsWith("/pilot-applications/verify/") && init?.method === "POST") return Promise.resolve(new Response(JSON.stringify({ verified: true, detail: "Your email is confirmed." }), { status: 200 }));
      return Promise.resolve(new Response("{}", { status: 200 }));
    });
    vi.stubGlobal("fetch", fetchMock);

    render(<App />);

    expect(await screen.findByText("Email confirmed")).toBeInTheDocument();
    expect(screen.getByText("Your email is confirmed.")).toBeInTheDocument();
    expect(window.location.search).not.toContain("pilot_token");
    expect(window.location.hash).toBe("#founding-10");
    await waitFor(() => expect(fetchMock.mock.calls.some(([input]) => String(input).endsWith("/pilot-applications/verify/"))).toBe(true));
  });

  it("strips private credentials from query strings without consuming them", async () => {
    window.history.replaceState(
      {},
      "",
      "/?invite_token=query-invite&reset_uid=query-uid&reset_token=query-reset&pilot_token=query-pilot&utm_source=linkedin",
    );
    const fetchMock = vi.fn((input: RequestInfo | URL) => {
      const path = String(input);
      if (path.endsWith("/healthz/")) return Promise.resolve(new Response(JSON.stringify({ status: "ok", database: "ok" }), { status: 200 }));
      if (path.endsWith("/me/")) return Promise.resolve(new Response("{}", { status: 401 }));
      return Promise.resolve(new Response("{}", { status: 200 }));
    });
    vi.stubGlobal("fetch", fetchMock);

    render(<App />);

    expect(await screen.findByRole("status")).toHaveTextContent("Ready for work");
    expect(window.location.search).toBe("?utm_source=linkedin");
    expect(
      fetchMock.mock.calls.some(([input]) =>
        /invitations\/inspect|password-reset\/inspect|pilot-applications\/verify/.test(String(input)),
      ),
    ).toBe(false);
  });

  it("turns a private invitation into a signed-in team account", async () => {
    window.history.replaceState({}, "", "/#invite_token=private-team-token");
    let joined = false;
    let acceptedPayload: Record<string, unknown> | undefined;
    const session = { user: { email: "amina@example.org", display_name: "Amina Hope" }, organizations: [{ organization: { id: "org-1", name: "North Star Centre", slug: "north-star-centre", status: "active" }, role: "staff" }] };
    const fetchMock = vi.fn((input: RequestInfo | URL, init?: RequestInit) => {
      const path = String(input);
      if (path.endsWith("/healthz/")) return Promise.resolve(new Response(JSON.stringify({ status: "ok", database: "ok" }), { status: 200 }));
      if (path.endsWith("/invitations/inspect/") && init?.method === "POST") return Promise.resolve(new Response(JSON.stringify({ organization: { name: "North Star Centre" }, email: "amina@example.org", role: "staff", roleLabel: "Staff", expiresAt: "2026-08-30T12:00:00Z", existingAccount: false }), { status: 200 }));
      if (path.endsWith("/invitations/accept/") && init?.method === "POST") {
        acceptedPayload = JSON.parse(String(init.body));
        joined = true;
        return Promise.resolve(new Response(JSON.stringify({ detail: "You have joined North Star Centre.", signedIn: true, createdAccount: true, organization: session.organizations[0].organization, user: session.user }), { status: 200 }));
      }
      if (path.endsWith("/me/")) return Promise.resolve(joined ? new Response(JSON.stringify(session), { status: 200 }) : new Response("{}", { status: 401 }));
      if (path.endsWith("/members/")) return Promise.resolve(new Response(JSON.stringify([{ id: "member-1", user: { id: "user-1", email: "amina@example.org", display_name: "Amina Hope" }, role: "staff", active: true }]), { status: 200 }));
      return Promise.resolve(new Response("{}", { status: 200 }));
    });
    vi.stubGlobal("fetch", fetchMock);

    render(<App />);
    expect(await screen.findByRole("heading", { name: "Join North Star Centre." })).toBeInTheDocument();
    expect(window.location.hash).toBe("");
    const invitationAccessibility = await axe.run(document.body, {
      runOnly: {
        type: "tag",
        values: ["wcag2a", "wcag2aa", "wcag21a", "wcag21aa", "wcag22aa"],
      },
      rules: { "color-contrast": { enabled: false } },
    });
    expect(invitationAccessibility.violations.map(({ id }) => id)).toEqual([]);
    fireEvent.change(screen.getByLabelText("First name"), { target: { value: "Amina" } });
    fireEvent.change(screen.getByLabelText("Last name"), { target: { value: "Hope" } });
    fireEvent.change(screen.getByLabelText("Password"), { target: { value: "Cedar-River-4827!" } });
    fireEvent.change(screen.getByLabelText("Confirm password"), { target: { value: "Cedar-River-4827!" } });
    fireEvent.click(screen.getByRole("button", { name: "Create account and join" }));

    expect(await screen.findByRole("heading", { name: "Team & access" })).toBeInTheDocument();
    expect(screen.getByText("You have joined North Star Centre.")).toBeInTheDocument();
    expect(acceptedPayload).toMatchObject({ token: "private-team-token", first_name: "Amina", last_name: "Hope" });
  });

  it("lets an owner invite staff and manage roles without technical tools", async () => {
    const organization = { id: "org-1", name: "Hope Demo", slug: "hope-demo", status: "active" };
    const session = { user: { email: "owner@example.org", display_name: "Demo Owner" }, organizations: [{ organization, role: "owner" }] };
    let invitations: unknown[] = [];
    let roleUpdate: Record<string, unknown> | undefined;
    let invitationPayload: Record<string, unknown> | undefined;
    const members = [
      { id: "owner-member", user: { id: "owner", email: "owner@example.org", display_name: "Demo Owner" }, role: "owner", active: true },
      { id: "staff-member", user: { id: "staff", email: "amina@example.org", display_name: "Amina Hope" }, role: "staff", active: true },
    ];
    const fetchMock = vi.fn((input: RequestInfo | URL, init?: RequestInit) => {
      const path = String(input);
      if (path.endsWith("/healthz/")) return Promise.resolve(new Response(JSON.stringify({ status: "ok", database: "ok" }), { status: 200 }));
      if (path.endsWith("/me/")) return Promise.resolve(new Response(JSON.stringify(session), { status: 200 }));
      if (path.endsWith("/members/staff-member/") && init?.method === "PATCH") {
        roleUpdate = JSON.parse(String(init.body));
        members[1].role = String(roleUpdate?.role ?? members[1].role);
        return Promise.resolve(new Response(JSON.stringify(members[1]), { status: 200 }));
      }
      if (path.endsWith("/members/")) return Promise.resolve(new Response(JSON.stringify(members), { status: 200 }));
      if (path.endsWith("/invitations/") && init?.method === "POST") {
        invitationPayload = JSON.parse(String(init.body));
        const invitation = { id: "invite-1", email: invitationPayload?.email, role: invitationPayload?.role, status: "pending", effective_status: "pending", delivery_status: "sent", expires_at: "2026-08-30T12:00:00Z", email_sent_at: "2026-08-23T12:00:00Z" };
        invitations = [invitation];
        return Promise.resolve(new Response(JSON.stringify(invitation), { status: 201 }));
      }
      if (path.endsWith("/invitations/")) return Promise.resolve(new Response(JSON.stringify(invitations), { status: 200 }));
      return Promise.resolve(new Response("{}", { status: 200 }));
    });
    vi.stubGlobal("fetch", fetchMock);

    render(<App />);
    const teamButtons = await screen.findAllByRole("button", { name: "Team & access" });
    fireEvent.click(teamButtons[0]);
    await screen.findByRole("button", { name: "Send invitation" });
    const teamAccessibility = await axe.run(document.body, {
      runOnly: {
        type: "tag",
        values: ["wcag2a", "wcag2aa", "wcag21a", "wcag21aa", "wcag22aa"],
      },
      rules: { "color-contrast": { enabled: false } },
    });
    expect(teamAccessibility.violations.map(({ id }) => id)).toEqual([]);
    fireEvent.change(screen.getByLabelText("Work email"), { target: { value: "new.staff@example.org" } });
    fireEvent.click(screen.getByRole("button", { name: "Send invitation" }));

    expect(await screen.findByText("Invitation sent to new.staff@example.org.")).toBeInTheDocument();
    expect(invitationPayload).toEqual({ email: "new.staff@example.org", role: "staff" });
    fireEvent.change(screen.getByRole("combobox", { name: "Role for Amina Hope" }), { target: { value: "coordinator" } });
    await waitFor(() => expect(roleUpdate).toEqual({ role: "coordinator" }));
  });

  it("shows owner access as protected when an administrator reviews the team", async () => {
    const organization = { id: "org-1", name: "Hope Demo", slug: "hope-demo", status: "active" };
    const session = { user: { email: "admin@example.org", display_name: "Demo Administrator" }, organizations: [{ organization, role: "admin" }] };
    const fetchMock = vi.fn((input: RequestInfo | URL) => {
      const path = String(input);
      if (path.endsWith("/healthz/")) return Promise.resolve(new Response(JSON.stringify({ status: "ok", database: "ok" }), { status: 200 }));
      if (path.endsWith("/me/")) return Promise.resolve(new Response(JSON.stringify(session), { status: 200 }));
      if (path.endsWith("/members/")) return Promise.resolve(new Response(JSON.stringify([
        { id: "owner-member", user: { id: "owner", email: "owner@example.org", display_name: "Founding Owner" }, role: "owner", active: true },
        { id: "admin-member", user: { id: "admin", email: "admin@example.org", display_name: "Demo Administrator" }, role: "admin", active: true },
      ]), { status: 200 }));
      if (path.endsWith("/invitations/")) return Promise.resolve(new Response(JSON.stringify([
        { id: "owner-invite", email: "second.owner@example.org", role: "owner", status: "pending", effective_status: "pending", delivery_status: "sent", expires_at: "2026-08-30T12:00:00Z", email_sent_at: "2026-08-23T12:00:00Z" },
      ]), { status: 200 }));
      return Promise.resolve(new Response("{}", { status: 200 }));
    });
    vi.stubGlobal("fetch", fetchMock);

    render(<App />);
    const teamButtons = await screen.findAllByRole("button", { name: "Team & access" });
    fireEvent.click(teamButtons[0]);

    const ownerRole = await screen.findByRole("combobox", { name: "Role for Founding Owner" });
    expect(ownerRole).toBeDisabled();
    expect(ownerRole).toHaveValue("owner");
    expect(screen.queryByRole("button", { name: "Resend" })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Revoke" })).not.toBeInTheDocument();
  });

  it("requests account recovery without revealing whether an account exists", async () => {
    let resetPayload: Record<string, unknown> | undefined;
    const fetchMock = vi.fn((input: RequestInfo | URL, init?: RequestInit) => {
      const path = String(input);
      if (path.endsWith("/healthz/")) return Promise.resolve(new Response(JSON.stringify({ status: "ok", database: "ok" }), { status: 200 }));
      if (path.endsWith("/me/")) return Promise.resolve(new Response("{}", { status: 401 }));
      if (path.endsWith("/auth/password-reset/") && init?.method === "POST") {
        resetPayload = JSON.parse(String(init.body));
        return Promise.resolve(new Response(JSON.stringify({ detail: "If an active account matches that email, private reset instructions will arrive shortly." }), { status: 202 }));
      }
      return Promise.resolve(new Response("{}", { status: 200 }));
    });
    vi.stubGlobal("fetch", fetchMock);

    render(<App />);
    fireEvent.click(await screen.findByRole("button", { name: "Forgot password?" }));
    expect(await screen.findByRole("heading", { name: "Reset your password." })).toBeInTheDocument();
    fireEvent.change(screen.getByLabelText("Account email"), { target: { value: "amina@example.org" } });
    fireEvent.click(screen.getByRole("button", { name: "Send reset link" }));

    expect(await screen.findByRole("heading", { name: "Check your inbox." })).toBeInTheDocument();
    expect(resetPayload).toEqual({ email: "amina@example.org" });
    expect(screen.getByText(/For privacy, the response is the same/i)).toBeInTheDocument();
  });

  it("uses a private reset fragment once and returns to sign in", async () => {
    window.history.replaceState({}, "", "/#reset_uid=private-uid&reset_token=private-reset-token");
    let confirmPayload: Record<string, unknown> | undefined;
    const fetchMock = vi.fn((input: RequestInfo | URL, init?: RequestInit) => {
      const path = String(input);
      if (path.endsWith("/healthz/")) return Promise.resolve(new Response(JSON.stringify({ status: "ok", database: "ok" }), { status: 200 }));
      if (path.endsWith("/me/")) return Promise.resolve(new Response("{}", { status: 401 }));
      if (path.endsWith("/auth/password-reset/inspect/") && init?.method === "POST") return Promise.resolve(new Response(JSON.stringify({ valid: true, email: "amina@example.org" }), { status: 200 }));
      if (path.endsWith("/auth/password-reset/confirm/") && init?.method === "POST") {
        confirmPayload = JSON.parse(String(init.body));
        return Promise.resolve(new Response(JSON.stringify({ detail: "Your password has been changed. Sign in with the new password.", email: "amina@example.org" }), { status: 200 }));
      }
      return Promise.resolve(new Response("{}", { status: 200 }));
    });
    vi.stubGlobal("fetch", fetchMock);

    render(<App />);
    expect(await screen.findByRole("heading", { name: "Choose a new password." })).toBeInTheDocument();
    expect(window.location.hash).toBe("");
    fireEvent.change(screen.getByLabelText("New password"), { target: { value: "Northern-Lights-9031!" } });
    fireEvent.change(screen.getByLabelText("Confirm new password"), { target: { value: "Northern-Lights-9031!" } });
    fireEvent.click(screen.getByRole("button", { name: "Change password" }));

    expect(await screen.findByText("Your password has been changed. Sign in with the new password.")).toBeInTheDocument();
    expect(screen.getByLabelText("Email")).toHaveValue("amina@example.org");
    expect(confirmPayload).toMatchObject({ uid: "private-uid", token: "private-reset-token" });
  });
});
