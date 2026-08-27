import assert from "node:assert/strict";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { fileURLToPath } from "node:url";
import runtimeModule from "../dist/runtime.js";

const { ShowcaseRuntime } = runtimeModule;
const desktop = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const profile = fs.mkdtempSync(path.join(os.tmpdir(), "hope-runtime-check-"));
const options = { appPath: desktop, resourcesPath: path.join(desktop, "resources"), userData: profile, packaged: true, onExit: () => {} };
let runtime = new ShowcaseRuntime(options);
let origin;
let cookies = new Map();

async function request(route, init = {}) {
  const headers = new Headers(init.headers);
  headers.set("X-Project-Hope-Desktop-Token", runtime.token);
  if (cookies.size) headers.set("Cookie", [...cookies].map(([key, value]) => `${key}=${value}`).join("; "));
  if (cookies.has("csrftoken")) headers.set("X-CSRFToken", cookies.get("csrftoken"));
  if (init.body && !(init.body instanceof FormData)) headers.set("Content-Type", "application/json");
  const response = await fetch(`${origin}${route}`, { ...init, headers, redirect: "manual", signal: AbortSignal.timeout(70_000) });
  for (const value of response.headers.getSetCookie()) {
    const pair = value.split(";")[0];
    const separator = pair.indexOf("=");
    cookies.set(pair.slice(0, separator), pair.slice(separator + 1));
  }
  return response;
}

async function open() {
  origin = await runtime.start();
  assert.equal((await fetch(`${origin}/api/v1/healthz/`)).status, 403, "untrusted local requests must be rejected");
  assert.equal((await request("/desktop/start/")).status, 302);
  assert.equal((await request("/api/v1/auth/csrf/")).status, 200);
  const health = await (await request("/api/v1/healthz/")).json();
  assert.equal(health.status, "ok");
  assert.equal(health.mode, "showcase");
  const me = await (await request("/api/v1/me/")).json();
  assert.equal(me.user.email, "showcase@example.org");
  assert.equal(me.organizations[0].organization.slug, "hope-showcase");
}

try {
  await open();
  const home = await request("/");
  assert.equal(home.status, 200);
  assert.match(await home.text(), /<div id="root"><\/div>/);
  assert.equal((await request("/api/v1/healthz/", { headers: { Origin: "https://untrusted.example" } })).status, 403);
  const base = "/api/v1/organizations/hope-showcase";
  for (const route of ["contacts", "volunteer-applications", "schedules", "documents", "email-drafts", "metrics", "grants", "resources", "translations", "accessibility-transforms", "calls", "donor-snapshots", "plugins", "api-clients", "workflows"]) {
    assert.equal((await request(`${base}/${route}/`)).status, 200, `${route} should load`);
  }
  let response = await request(`${base}/contacts/`, { method: "POST", body: JSON.stringify({ first_name: "Runtime", last_name: "Check", email: "runtime.check@example.org", notes: "Synthetic packaging check" }) });
  assert.equal(response.status, 201);
  const contact = await response.json();
  response = await request(`${base}/contacts/${contact.id}/`, { method: "PATCH", body: JSON.stringify({ notes: "Persists after restarting the packaged runtime" }) });
  assert.equal(response.status, 200);
  const csv = await (await request(`${base}/crm/export/?fileFormat=csv`)).text();
  assert.match(csv, /runtime.check@example.org/);
  const duplicateResponse = await (await request(`${base}/crm/duplicates/`)).json();
  assert.ok(duplicateResponse.results.length > 0, "sample includes a reviewable duplicate");
  response = await request(`${base}/ai/v1/classify-intent/`, { method: "POST", body: JSON.stringify({ text: "I would like to volunteer at the community pantry." }) });
  assert.equal(response.status, 200);
  assert.ok((await response.json()).workflowId);
  assert.equal((await request(`${base}/email-drafts/${contact.id}/send/`, { method: "POST", body: "{}" })).status, 403);
  assert.equal((await request(`${base}/invitations/`, { method: "POST", body: JSON.stringify({ email: "nobody@example.org", role: "staff" }) })).status, 403);
  runtime.stop();
  await new Promise((resolve) => setTimeout(resolve, 1800));
  runtime = new ShowcaseRuntime(options);
  cookies = new Map();
  await open();
  response = await request(`${base}/contacts/${contact.id}/`);
  assert.equal(response.status, 200);
  assert.equal((await response.json()).notes, "Persists after restarting the packaged runtime");
  console.log("PASS: bundled startup, auto sign-in, 15 module routes, CRM edits/export/duplicates, bounded AI, external-action blocking, and restart persistence.");
} finally {
  runtime.stop();
}
