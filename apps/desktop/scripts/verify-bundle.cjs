const fs = require("node:fs");
const path = require("node:path");

module.exports = async (context) => {
  const base = path.resolve(__dirname, "../resources");
  const executable = context.electronPlatformName === "win32" ? "project-hope-core.exe" : "project-hope-core";
  for (const file of [path.join(base, "runtime/project-hope-core", executable), path.join(base, "web/index.html")]) {
    if (!fs.existsSync(file)) throw new Error("Refusing to publish an incomplete installer. Run build:bundle to include the workspace engine and web app.");
  }
};
