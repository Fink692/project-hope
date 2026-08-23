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
    expect(screen.getByRole("main")).toHaveAttribute("id", "main-content");
    expect(await screen.findByRole("status")).toHaveTextContent("Ready for local work");
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
        return Promise.resolve(new Response(JSON.stringify({ token: "test-token" }), { status: 200 }));
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
});
