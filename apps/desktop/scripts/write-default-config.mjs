import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const scriptDirectory = path.dirname(fileURLToPath(import.meta.url));
const appDirectory = path.resolve(scriptDirectory, "..");
const serverUrl = (process.env.PROJECT_HOPE_APP_URL ?? "").trim().replace(/\/$/, "");

fs.writeFileSync(
  path.join(appDirectory, "dist", "default-config.json"),
  `${JSON.stringify({ serverUrl }, null, 2)}\n`,
  "utf8",
);
