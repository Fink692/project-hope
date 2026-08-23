import { writeFile } from "node:fs/promises";
import { createHmac } from "node:crypto";

const outputPath = process.argv[2];
const appUrl = process.argv[3] ?? "http://127.0.0.1:5173/";
const email = process.argv[4] ?? "demo@example.org";
const password = process.argv[5] ?? "change-me-now";
const recoveryOutputPath = process.argv[6];
const debuggingOrigin = process.env.CHROME_DEBUG_ORIGIN ?? "http://127.0.0.1:9222";

if (!outputPath) {
  throw new Error("Usage: node scripts/capture-browser-mfa.mjs OUTPUT [URL] [EMAIL] [PASSWORD] [RECOVERY_OUTPUT]");
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

function currentTotp(base32Secret) {
  const alphabet = "ABCDEFGHIJKLMNOPQRSTUVWXYZ234567";
  let bits = "";
  for (const character of base32Secret.replace(/\s+/g, "").toUpperCase()) {
    const value = alphabet.indexOf(character);
    if (value < 0) throw new Error("Authenticator secret is not valid base32.");
    bits += value.toString(2).padStart(5, "0");
  }
  const bytes = [];
  for (let index = 0; index + 8 <= bits.length; index += 8) {
    bytes.push(Number.parseInt(bits.slice(index, index + 8), 2));
  }
  const counter = Buffer.alloc(8);
  counter.writeBigUInt64BE(BigInt(Math.floor(Date.now() / 30_000)));
  const digest = createHmac("sha1", Buffer.from(bytes)).update(counter).digest();
  const offset = digest[digest.length - 1] & 0x0f;
  const value =
    (((digest[offset] & 0x7f) << 24) |
      (digest[offset + 1] << 16) |
      (digest[offset + 2] << 8) |
      digest[offset + 3]) %
    1_000_000;
  return String(value).padStart(6, "0");
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

async function waitFor(expression, timeoutMs = 12_000) {
  const deadline = Date.now() + timeoutMs;
  while (Date.now() < deadline) {
    if (await evaluate(expression)) return;
    await new Promise((resolve) => setTimeout(resolve, 150));
  }
  const pageText = await evaluate("document.body?.innerText?.slice(0, 1000) ?? ''");
  throw new Error(`Timed out waiting for browser state: ${expression}\n${pageText}`);
}

await command("Page.enable");
await command("Runtime.enable");
await command("Network.enable");
await command("Network.clearBrowserCookies");
await command("Emulation.setDeviceMetricsOverride", {
  width: 1440,
  height: 1000,
  deviceScaleFactor: 1,
  mobile: false,
});
await command("Page.navigate", { url: appUrl });
await waitFor("document.readyState === 'complete' && Boolean(document.querySelector('form.sign-in-form'))");

await evaluate("document.querySelector('form.sign-in-form input[type=\"email\"]').focus(); true");
await command("Input.insertText", { text: email });
await evaluate("document.querySelector('form.sign-in-form input[type=\"password\"]').focus(); true");
await command("Input.insertText", { text: password });
await new Promise((resolve) => setTimeout(resolve, 100));
await evaluate("document.querySelector('form.sign-in-form button[type=\"submit\"]').click(); true");

await waitFor("document.body.innerText.includes('Protect this account before continuing.')");
await evaluate(`(() => {
  const label = [...document.querySelectorAll("label")].find((item) => item.textContent.includes("Current password"));
  const input = label?.querySelector("input");
  if (!input) return false;
  input.focus();
  return true;
})()`);
await command("Input.insertText", { text: password });
await new Promise((resolve) => setTimeout(resolve, 100));
await evaluate(`(() => {
  const button = [...document.querySelectorAll("button")].find((item) => item.textContent.includes("Set up two-step verification"));
  if (!button) return false;
  button.click();
  return true;
})()`);

await waitFor("Boolean(document.querySelector('img[alt^=\"Authenticator setup QR code\"]'))");
const authenticatorSecret = await evaluate(
  "document.querySelector('.manual-secret').textContent.replace(/\\s+/g, '')",
);
await evaluate(`(() => {
  document.documentElement.style.scrollBehavior = "auto";
  const image = document.querySelector(".mfa-qr img");
  const imageCard = document.querySelector(".mfa-qr");
  const manualSecret = document.querySelector(".manual-secret");
  const firstTimeIdentity = document.querySelector(".workspace-header .eyebrow");
  if (!document.querySelector(".workspace-header select")) firstTimeIdentity?.remove();
  if (image && imageCard) {
    image.style.visibility = "hidden";
    imageCard.style.background = "linear-gradient(145deg, #edf4ef, #f8f4ec)";
    imageCard.style.position = "relative";
    const notice = document.createElement("strong");
    notice.innerHTML = '<span style="font-size:38px" aria-hidden="true">🔒</span><span>Private demo QR redacted</span>';
    notice.style.cssText = "position:absolute;inset:30% 10%;display:grid;place-items:center;padding:14px;background:#fff;border:1px solid #b9d1c0;border-radius:14px;text-align:center;color:#1f5148;z-index:2";
    imageCard.appendChild(notice);
  }
  if (manualSecret) manualSecret.textContent = "PRIVATE DEMO KEY REDACTED";
  const workspace = document.getElementById("workspace");
  if (workspace) window.scrollTo(0, window.scrollY + workspace.getBoundingClientRect().top - 40);
  return new Promise((resolve) => setTimeout(() => resolve(true), 250));
})()`);
const screenshot = await command("Page.captureScreenshot", {
  format: "png",
  fromSurface: true,
  captureBeyondViewport: false,
});
await writeFile(outputPath, Buffer.from(screenshot.data, "base64"));

if (recoveryOutputPath) {
  const verificationCode = currentTotp(authenticatorSecret);
  await evaluate("document.querySelector('input[autocomplete=\"one-time-code\"]').focus(); true");
  await command("Input.insertText", { text: verificationCode });
  await new Promise((resolve) => setTimeout(resolve, 100));
  await evaluate(`(() => {
    const button = [...document.querySelectorAll("button")].find((item) => item.textContent.includes("Verify and turn on"));
    if (!button) return false;
    button.click();
    return true;
  })()`);
  await waitFor("document.body.innerText.includes('Save your recovery codes.')");
  await evaluate(`(() => {
    document.querySelectorAll(".recovery-code-card code").forEach((item) => { item.textContent = "•••••-•••••"; });
    const card = document.querySelector(".recovery-code-card");
    if (card) {
      const notice = document.createElement("p");
      notice.textContent = "Live demo codes redacted for this release image.";
      notice.style.cssText = "font-weight:700;color:#8f2f1f";
      card.insertBefore(notice, card.querySelector("ul"));
    }
    const workspace = document.getElementById("workspace");
    if (workspace) window.scrollTo(0, window.scrollY + workspace.getBoundingClientRect().top - 40);
    return new Promise((resolve) => setTimeout(() => resolve(true), 250));
  })()`);
  const recoveryScreenshot = await command("Page.captureScreenshot", {
    format: "png",
    fromSurface: true,
    captureBeyondViewport: false,
  });
  await writeFile(
    recoveryOutputPath,
    Buffer.from(recoveryScreenshot.data, "base64"),
  );
}
await command("Page.close");
socket.close();

console.log(`Captured ${outputPath}`);
if (recoveryOutputPath) console.log(`Captured ${recoveryOutputPath}`);
