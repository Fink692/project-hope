import { writeFile } from "node:fs/promises";

const importOutputPath = process.argv[2];
const duplicateOutputPath = process.argv[3];
const appUrl = process.argv[4] ?? "http://127.0.0.1:5173/";
const email = process.argv[5] ?? "demo@example.org";
const password = process.argv[6] ?? "change-me-now";
const debuggingOrigin = process.env.CHROME_DEBUG_ORIGIN ?? "http://127.0.0.1:9222";

if (!importOutputPath || !duplicateOutputPath) {
  throw new Error(
    "Usage: node scripts/capture-browser-crm.mjs IMPORT_OUTPUT DUPLICATE_OUTPUT [URL] [EMAIL] [PASSWORD]",
  );
}

const targetResponse = await fetch(
  `${debuggingOrigin}/json/new?${encodeURIComponent(appUrl)}`,
  { method: "PUT" },
);
if (!targetResponse.ok) {
  throw new Error(`Chrome target creation failed (${targetResponse.status}).`);
}
const target = await targetResponse.json();
const socket = new WebSocket(target.webSocketDebuggerUrl);
await new Promise((resolve, reject) => {
  socket.addEventListener("open", resolve, { once: true });
  socket.addEventListener("error", reject, { once: true });
});

let commandId = 0;
const pending = new Map();
socket.addEventListener("message", (event) => {
  const message = JSON.parse(String(event.data));
  if (!message.id || !pending.has(message.id)) return;
  const { resolve, reject } = pending.get(message.id);
  pending.delete(message.id);
  if (message.error) reject(new Error(message.error.message));
  else resolve(message.result);
});

function command(method, params = {}) {
  commandId += 1;
  const id = commandId;
  socket.send(JSON.stringify({ id, method, params }));
  return new Promise((resolve, reject) => pending.set(id, { resolve, reject }));
}

async function evaluate(expression) {
  const result = await command("Runtime.evaluate", {
    expression,
    awaitPromise: true,
    returnByValue: true,
  });
  if (result.exceptionDetails) {
    throw new Error(
      result.exceptionDetails.exception?.description ??
        result.exceptionDetails.text ??
        "Browser evaluation failed.",
    );
  }
  return result.result.value;
}

async function waitFor(expression, timeoutMs = 15_000) {
  const deadline = Date.now() + timeoutMs;
  while (Date.now() < deadline) {
    if (await evaluate(expression)) return;
    await new Promise((resolve) => setTimeout(resolve, 150));
  }
  const pageText = await evaluate("document.body?.innerText?.slice(0, 1600) ?? ''");
  throw new Error(`Timed out waiting for browser state: ${expression}\n${pageText}`);
}

async function capture(path) {
  const screenshot = await command("Page.captureScreenshot", {
    format: "png",
    fromSurface: true,
    captureBeyondViewport: false,
  });
  await writeFile(path, Buffer.from(screenshot.data, "base64"));
}

await command("Page.enable");
await command("Runtime.enable");
await command("Network.enable");
await command("Network.clearBrowserCookies");
await command("Emulation.setDeviceMetricsOverride", {
  width: 1600,
  height: 1200,
  deviceScaleFactor: 1,
  mobile: false,
});
await command("Page.navigate", { url: appUrl });
await waitFor("document.readyState === 'complete' && Boolean(document.querySelector('form.sign-in-form'))");

await evaluate("document.querySelector('form.sign-in-form input[type=\"email\"]').focus(); true");
await command("Input.insertText", { text: email });
await evaluate("document.querySelector('form.sign-in-form input[type=\"password\"]').focus(); true");
await command("Input.insertText", { text: password });
await evaluate("document.querySelector('form.sign-in-form button[type=\"submit\"]').click(); true");
await waitFor("Boolean(document.querySelector('.workspace'))");

await evaluate(`(() => {
  const button = [...document.querySelectorAll(".module-nav button")]
    .find((item) => item.textContent.trim() === "CRM");
  if (!button) return false;
  button.click();
  return true;
})()`);
await waitFor("Boolean(document.querySelector('.crm-panel'))");
await evaluate(`(() => {
  const button = [...document.querySelectorAll(".crm-view-nav button")]
    .find((item) => item.textContent.trim() === "Import & export");
  if (!button) return false;
  button.click();
  return true;
})()`);
await waitFor("Boolean(document.querySelector('#crm-import-file'))");

const csv = [
  "First Name,Last Name,Email Address,Phone Number,External Reference,Consent,Notes,Old category",
  "Samira,Patel,samira@northstar.example,+1 204 555 0188,LEGACY-104,granted,Volunteer coordinator,Active",
  "Amina,Hope,AMINA@northstar.example,+1 204 555 0100,LEGACY-101,granted,Updated phone from source,Supporter",
  "Luis,Chen,,204-555-0199,,unknown,Neighbourhood outreach,Participant",
  "Jordan,River,not-an-email,,,,Needs correction,Volunteer",
].join("\n");

await evaluate(`(() => {
  const input = document.querySelector("#crm-import-file");
  const transfer = new DataTransfer();
  transfer.items.add(new File([${JSON.stringify(csv)}], "north-star-contacts.csv", { type: "text/csv" }));
  input.files = transfer.files;
  input.dispatchEvent(new Event("change", { bubbles: true }));
  return true;
})()`);
await waitFor("!document.querySelector('.import-picker button[type=\"submit\"]').disabled");
await evaluate("document.querySelector('.import-picker button[type=\"submit\"]').click(); true");
await waitFor("Boolean(document.querySelector('#import-review-title'))");

await evaluate(`(() => {
  document.documentElement.style.scrollBehavior = "auto";
  const panel = document.querySelector(".crm-panel");
  if (panel && !panel.querySelector(".release-demo-badge")) {
    const badge = document.createElement("p");
    badge.className = "release-demo-badge";
    badge.textContent = "Release demonstration · synthetic contacts only";
    badge.style.cssText = "position:sticky;top:8px;z-index:5;margin:0 0 14px;padding:9px 12px;border:1px solid #9bc2a5;border-radius:10px;background:#e7f4e9;color:#245d3b;font-size:12px;font-weight:800;text-align:center;box-shadow:0 5px 16px rgba(44,58,50,.08)";
    panel.prepend(badge);
  }
  document.querySelectorAll(".migration-tools, .import-picker").forEach((item) => {
    item.style.display = "none";
  });
  if (panel) window.scrollTo(0, window.scrollY + panel.getBoundingClientRect().top - 18);
  return new Promise((resolve) => setTimeout(() => resolve(true), 350));
})()`);
await capture(importOutputPath);

await evaluate(`(() => {
  const button = [...document.querySelectorAll(".crm-view-nav button")]
    .find((item) => item.textContent.trim() === "Find duplicates");
  if (!button) return false;
  button.click();
  return true;
})()`);
await waitFor("Boolean(document.querySelector('.duplicate-card'))");
await evaluate(`(() => {
  const workspace = document.getElementById("workspace");
  if (workspace) window.scrollTo(0, window.scrollY + workspace.getBoundingClientRect().top - 18);
  return new Promise((resolve) => setTimeout(() => resolve(true), 350));
})()`);
await capture(duplicateOutputPath);

await command("Page.close");
socket.close();

console.log(`Captured ${importOutputPath}`);
console.log(`Captured ${duplicateOutputPath}`);
