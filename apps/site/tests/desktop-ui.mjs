import assert from "node:assert/strict";
import fs from "node:fs/promises";
import os from "node:os";
import path from "node:path";
import { _electron as electron } from "playwright";

const executablePath = process.argv[2];
assert.ok(executablePath, "Pass the packaged Project Hope executable as the first argument.");
const profile = await fs.mkdtemp(path.join(os.tmpdir(), "hope-desktop-ui-"));
const output = path.resolve("artifacts");
await fs.mkdir(output, { recursive: true });
const application = await electron.launch({
  executablePath,
  env: { ...process.env, PROJECT_HOPE_DESKTOP_PROFILE: profile },
  timeout: 120_000,
});
try {
  const page = await application.firstWindow();
  const errors = [];
  page.on("pageerror", (error) => errors.push(error.message));
  await page.locator(".workspace").waitFor({ timeout: 120_000 });
  const version = await application.evaluate(({ app }) => app.getVersion());
  assert.equal(version, "1.9.0");
  assert.match(page.url(), /^http:\/\/127\.0\.0\.1:\d+/);
  assert.equal(await page.locator("a[href*='github']").count(), 0);
  await page.locator(".showcase-banner").waitFor({ timeout: 15_000 });
  await page.getByRole("button", { name: "CRM", exact: true }).click();
  await page.locator(".crm-panel").waitFor();
  await page.screenshot({ path: path.join(output, "desktop-app-contacts.png") });
  const aiButton = page.getByRole("button", { name: "AI workflows", exact: true });
  await aiButton.click();
  await page.getByRole("button", { name: "Use a fictional sample" }).click();
  await page.locator(".ai-input-form").getByRole("button", { name: "Draft a reply", exact: true }).click();
  await page.getByRole("heading", { name: "Ready for your review" }).waitFor({ timeout: 100_000 });
  assert.ok((await page.getByLabel("Draft result").inputValue()).length > 20);
  assert.equal(await page.getByRole("button", { name: /^send/i }).count(), 0);
  const modelResult = await page.locator(".ai-result-heading span").textContent();
  await page.screenshot({ path: path.join(output, "desktop-app-assistant.png") });
  await page.getByRole("button", { name: "Connect my charity", exact: true }).first().click();
  await page.locator("#connection-details summary").click();
  await page.getByLabel("Workspace website — not your email").fill("demo@example.org");
  await page.getByRole("button", { name: "Connect my workspace" }).click();
  await page.locator("#status.error").waitFor();
  assert.match(await page.locator("#status").textContent(), /email/i);
  await page.getByRole("button", { name: "Open sample workspace" }).click();
  await page.locator(".workspace").waitFor({ timeout: 60_000 });
  assert.deepEqual(errors, []);
  console.log("PASS: packaged Electron " + version + " opens its real sample automatically; CRM and writing UI work; result label: " + modelResult + "; no external send or repository links; email/address validation and returning to sample work.");
} finally { await application.close(); }
