import { spawn, type ChildProcessWithoutNullStreams } from "node:child_process";
import { randomBytes } from "node:crypto";
import fs from "node:fs";
import path from "node:path";
import { isRuntimeOrigin } from "./connection";

export class ShowcaseRuntime {
  private child: ChildProcessWithoutNullStreams | null = null;
  private pending: Promise<string> | null = null;
  private stopping = false;
  origin = "";
  readonly token = randomBytes(48).toString("hex");

  constructor(private options: { appPath: string; resourcesPath: string; userData: string; packaged: boolean; onExit: () => void }) {}

  start(): Promise<string> {
    if (this.origin && this.child && this.child.exitCode === null) return Promise.resolve(this.origin);
    if (this.pending) return this.pending;
    this.pending = this.launch().finally(() => { this.pending = null; });
    return this.pending;
  }

  private launch(): Promise<string> {
    const { appPath, resourcesPath, userData, packaged } = this.options;
    const root = packaged ? resourcesPath : path.join(appPath, "resources");
    const binary = path.join(root, "runtime", "project-hope-core", process.platform === "win32" ? "project-hope-core.exe" : "project-hope-core");
    const core = path.resolve(appPath, "../../services/core");
    const bundled = fs.existsSync(binary);
    const command = bundled ? binary : (process.env.PROJECT_HOPE_PYTHON || path.join(core, ".venv", process.platform === "win32" ? "Scripts/python.exe" : "bin/python"));
    const webRoot = bundled ? path.join(root, "web") : path.resolve(appPath, "../web/dist");
    if ((packaged && !bundled) || !fs.existsSync(command) || !fs.existsSync(path.join(webRoot, "index.html"))) {
      return Promise.reject(new Error("The app is missing its workspace files. Please download and reinstall the latest complete installer."));
    }
    const dataDir = path.join(userData, "showcase");
    const logDir = path.join(userData, "logs");
    fs.mkdirSync(logDir, { recursive: true });
    const logPath = path.join(logDir, "showcase.log");
    const log = (chunk: string) => {
      try {
        if (!fs.existsSync(logPath) || fs.statSync(logPath).size < 2 * 1024 * 1024) fs.appendFileSync(logPath, chunk.replaceAll(this.token, "[redacted]"));
      } catch { /* Logging must not stop a working workspace. */ }
    };
    const args = [...(bundled ? [] : [path.join(core, "desktop_runtime.py")]), "--data-dir", dataDir, "--web-root", webRoot];
    const env: NodeJS.ProcessEnv = {};
    for (const key of ["PATH", "Path", "SystemRoot", "SYSTEMROOT", "WINDIR", "TEMP", "TMP", "HOME", "USERPROFILE", "LOCALAPPDATA", "APPDATA", "LANG", "LC_ALL"]) {
      if (process.env[key]) env[key] = process.env[key];
    }
    env.PROJECT_HOPE_DESKTOP_TOKEN = this.token;
    env.PYTHONUNBUFFERED = "1";
    env.PYTHONIOENCODING = "utf-8";
    this.stopping = false;
    return new Promise((resolve, reject) => {
      const child = spawn(command, args, { env, windowsHide: true, stdio: "pipe" });
      this.child = child;
      child.stdin.on("error", () => undefined);
      let buffer = "";
      let settled = false;
      const fail = (message: string) => {
        if (settled) return;
        settled = true;
        clearTimeout(timeout);
        this.stop();
        reject(new Error(message));
      };
      const timeout = setTimeout(() => fail("Preparing the sample workspace took too long. Close Project Hope and try again."), 120_000);
      child.stdout.setEncoding("utf8");
      child.stderr.setEncoding("utf8");
      child.stderr.on("data", (data: string) => log(data));
      child.stdout.on("data", (chunk: string) => {
        buffer += chunk;
        if (buffer.length > 64 * 1024) { fail("The workspace returned an unexpected startup response."); return; }
        let boundary: number;
        while ((boundary = buffer.indexOf("\n")) >= 0) {
          const line = buffer.slice(0, boundary).trim();
          buffer = buffer.slice(boundary + 1);
          try {
            const result = JSON.parse(line);
            if (result.event === "ready" && isRuntimeOrigin(result.url) && !settled) {
              settled = true;
              clearTimeout(timeout);
              this.origin = result.url;
              resolve(result.url);
            } else if (result.event === "error") fail("The sample workspace could not start. Try reopening the app, or reinstall the latest version.");
          } catch { log(`${line}\n`); }
        }
      });
      child.once("error", () => fail("Project Hope could not start its workspace engine. Reinstall the latest complete installer."));
      child.once("exit", () => {
        clearTimeout(timeout);
        const isCurrentChild = this.child === child;
        if (isCurrentChild) { this.origin = ""; this.child = null; }
        if (!settled) fail("The workspace engine stopped before it was ready. Try reopening Project Hope.");
        else if (isCurrentChild && !this.stopping) this.options.onExit();
      });
    });
  }

  stop(): void {
    this.stopping = true;
    const child = this.child;
    this.child = null;
    this.origin = "";
    if (!child || child.exitCode !== null) return;
    child.stdin.end("shutdown\n");
    const fallback = setTimeout(() => { if (child.exitCode === null) child.kill(); }, 1500);
    fallback.unref();
  }
}
