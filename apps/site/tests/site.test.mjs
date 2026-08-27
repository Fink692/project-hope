import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import test from "node:test";
const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const manifest = JSON.parse(fs.readFileSync(path.join(root, "lib/release-manifest.json"), "utf8"));
const config = JSON.parse(fs.readFileSync(path.join(root, "vercel.json"), "utf8"));
test("every advertised installer is versioned, unique, and integrity-checked", () => {
  assert.equal(new Set(manifest.assets.map((asset) => asset.file)).size, manifest.assets.length);
  for (const asset of manifest.assets) {
    assert.ok(asset.file.startsWith("Project-Hope-" + manifest.version + "-"));
    assert.ok(!asset.file.includes("/") && !asset.file.includes(".."));
    if (asset.available) {
      assert.match(asset.sha256, /^[a-f0-9]{64}$/);
      assert.ok(asset.bytes > 1_000_000);
    }
  }
});
test("the public app has no repository links or former hosting dependencies", () => {
  for (const file of fs.readdirSync(path.join(root, "app"), { recursive: true })) {
    if (/\.(tsx|ts)$/.test(file)) assert.doesNotMatch(fs.readFileSync(path.join(root, "app", file), "utf8"), /github\.com|gpt-sites|sites\.chatgpt/i, file);
  }
  const pkg = fs.readFileSync(path.join(root, "package.json"), "utf8");
  assert.doesNotMatch(pkg, /vinext|sites-vite|cloudflare/);
  assert.equal(config.framework, "nextjs");
});
test("the new logo and on-site help routes exist", () => {
  assert.equal(fs.readFileSync(path.join(root, "public/hope-mark.png")).subarray(1, 4).toString(), "PNG");
  for (const route of ["guide", "privacy", "release-notes"]) assert.ok(fs.existsSync(path.join(root, "app", route, "page.tsx")));
});
test("download responses are attachments and cannot be interpreted as HTML", () => {
  const downloadHeaders = config.headers.find((rule) => rule.source.startsWith("/downloads/")).headers;
  assert.ok(downloadHeaders.some((header) => header.key === "Content-Disposition" && header.value === "attachment"));
  assert.ok(config.headers[0].headers.some((header) => header.key === "X-Content-Type-Options" && header.value === "nosniff"));
  for (const rewrite of config.rewrites || []) assert.doesNotMatch(rewrite.destination, /github|api\.github/i);
});
