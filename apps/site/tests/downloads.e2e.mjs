import assert from "node:assert/strict";
import { createHash } from "node:crypto";
import fs from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { chromium } from "playwright";

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const manifest = JSON.parse(await fs.readFile(path.join(root, "lib/release-manifest.json"), "utf8"));
const base = new URL(process.env.HOPE_SITE_URL || "http://localhost:5180");
assert.ok(manifest.published && manifest.assets.every((asset) => asset.available), "Publish verified installers before running live download checks.");

for (const asset of manifest.assets) {
  const url = new URL("/downloads/" + encodeURIComponent(asset.file), base);
  const response = await fetch(url, { redirect: "manual", signal: AbortSignal.timeout(240_000) });
  assert.equal(response.status, 200, asset.file + " must download without a redirect");
  assert.equal(response.headers.get("location"), null);
  assert.match(response.headers.get("content-disposition") || "", /attachment/i);
  assert.equal(response.headers.get("x-content-type-options"), "nosniff");
  assert.doesNotMatch(response.headers.get("content-type") || "", /text\/html/i);
  const hash = createHash("sha256");
  let bytes = 0;
  for await (const chunk of response.body) {
    hash.update(chunk);
    bytes += chunk.length;
  }
  assert.equal(bytes, asset.bytes, asset.file + " must have the published length");
  assert.equal(hash.digest("hex"), asset.sha256, asset.file + " must match its published checksum");
  console.log("PASS: direct download, byte length, and SHA-256 — " + asset.file);
}

for (const feed of ["latest.yml", "latest-mac.yml", "latest-linux.yml"]) {
  const response = await fetch(new URL("/downloads/" + feed, base), { redirect: "manual", signal: AbortSignal.timeout(30_000) });
  assert.equal(response.status, 200, feed);
  const body = await response.text();
  assert.ok(body.includes("version: " + manifest.version), feed + " must describe this release");
  assert.doesNotMatch(body, /github/i);
  console.log("PASS: same-site update feed — " + feed);
}

const browser = await chromium.launch({ channel: process.env.E2E_BROWSER_CHANNEL || (process.platform === "win32" ? "chrome" : undefined), headless: true });
try {
  const page = await browser.newPage({ acceptDownloads: true, reducedMotion: "reduce" });
  await page.goto(base.href + "#download", { waitUntil: "networkidle" });
  const downloadEvent = page.waitForEvent("download", { timeout: 30_000 });
  await page.getByRole("link", { name: "Download for Windows", exact: false }).click();
  const download = await downloadEvent;
  const expected = manifest.assets.find((asset) => asset.file.endsWith("-win-x64.exe"));
  assert.equal(download.suggestedFilename(), expected.file);
  assert.equal(new URL(download.url()).origin, base.origin);
  assert.equal(await download.failure(), null, "The browser must complete the installer download");
  assert.match(await page.getByRole("status").textContent(), /Windows download should start/);
  console.log("PASS: the visible Windows button completes a same-site browser download with the correct filename.");
} finally {
  await browser.close();
}
