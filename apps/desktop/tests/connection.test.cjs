const assert = require("node:assert/strict");
const { test } = require("node:test");
const { normalizeServerUrl, isExternalWebUrl, isRuntimeOrigin } = require("../dist/connection.js");

test("workspace addresses distinguish email from the later login", () => {
  assert.throws(() => normalizeServerUrl("demo@example.org"), /email address/);
  assert.equal(normalizeServerUrl(" https://hope.example.org/ "), "https://hope.example.org");
});
test("only HTTPS or explicit loopback HTTP workspace addresses are accepted", () => {
  for (const value of ["http://example.org", "file:///tmp/site", "javascript:alert(1)", "https://user:pass@example.org", "https://example.org?token=secret", "https://example.org#secret"]) assert.throws(() => normalizeServerUrl(value));
  for (const value of ["http://localhost:8090", "http://127.0.0.1:5173", "http://[::1]:8090"]) assert.equal(normalizeServerUrl(value), value);
});
test("external navigation never opens executables or custom URL schemes", () => {
  for (const value of ["file:///C:/Windows/notepad.exe", "powershell:run", "javascript:alert(1)", "https://user:password@example.org"]) assert.equal(isExternalWebUrl(value), false);
  assert.equal(isExternalWebUrl("https://github.com/Fink692/project-hope"), true);
});
test("the bundled process can only announce a literal loopback origin", () => {
  assert.equal(isRuntimeOrigin("http://127.0.0.1:49201"), true);
  for (const value of [null, "https://example.org", "http://localhost:4000", "http://127.0.0.1:4000/path", "http://127.0.0.1:4000?secret", "http://user@127.0.0.1:4000"]) assert.equal(isRuntimeOrigin(value), false);
});
