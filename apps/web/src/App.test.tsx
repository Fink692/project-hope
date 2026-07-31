import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import App from "./App";

describe("Project Hope web shell", () => {
  afterEach(() => cleanup());

  beforeEach(() => {
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
    expect(screen.getByRole("main")).toHaveAttribute("id", "main-content");
    expect(await screen.findByRole("status")).toHaveTextContent("Ready for local work");
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
});
