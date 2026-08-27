import assert from "node:assert/strict";
import { createReadStream } from "node:fs";
import { stat } from "node:fs/promises";
import { createHash } from "node:crypto";
import path from "node:path";
import { put, head } from "@vercel/blob";

// The linked Vercel project writes this ignored file. Credentials never become
// command-line arguments, browser code, or upload output.
try { process.loadEnvFile(".env.local"); } catch { /* CI may supply its environment directly. */ }
const token = process.env.BLOB_READ_WRITE_TOKEN;
assert.ok(token, "Link the Vercel project and pull its Blob environment before publishing.");
const file = process.argv[2];
const pathname = process.argv[3] || (file && path.basename(file));
const replaceFeed = process.argv[4] === "--replace-feed";
const feedNames = new Set(["latest.yml", "latest-mac.yml", "latest-linux.yml", "SHA256SUMS.txt"]);
assert.ok(file && pathname, "Usage: node scripts/publish-blob.mjs FILE [PUBLIC_PATH] [--replace-feed]");
assert.ok(!pathname.startsWith("/") && !pathname.split("/").includes(".."), "Use a safe relative blob path.");
assert.ok(!replaceFeed || feedNames.has(pathname), "Only an explicit current-release feed may be replaced; versioned installers are immutable.");
assert.ok(process.argv.length <= 4 || replaceFeed, "Unknown publishing option.");
const hash = createHash("sha256");
for await (const chunk of createReadStream(file)) hash.update(chunk);
const sha256 = hash.digest("hex");
const metadata = await stat(file);
const blob = await put(pathname, createReadStream(file), {
  access: "public",
  token,
  addRandomSuffix: false,
  allowOverwrite: replaceFeed,
  multipart: metadata.size > 8 * 1024 * 1024,
  cacheControlMaxAge: feedNames.has(pathname) ? 60 : 31536000,
});
const stored = await head(blob.url, { token });
assert.equal(stored.size, metadata.size, "The stored file must match the uploaded byte length.");
console.log(JSON.stringify({ file: path.basename(file), pathname, bytes: stored.size, sha256, url: blob.url }));
