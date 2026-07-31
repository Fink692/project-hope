import { app, BrowserWindow, ipcMain, shell } from "electron";
import { autoUpdater } from "electron-updater";
import fs from "node:fs";
import path from "node:path";

type DesktopConfig = {
  serverUrl?: string;
};

type ConnectionResult = {
  ok: boolean;
  url?: string;
  message: string;
};

const settingsPath = () => path.join(app.getPath("userData"), "settings.json");
let mainWindow: BrowserWindow | null = null;
let activeServerUrl = "";

function normalizeServerUrl(value: unknown): string {
  if (typeof value !== "string" || !value.trim()) throw new Error("Enter your Project Hope workspace address.");
  const parsed = new URL(value.trim());
  const localDevelopmentHost = ["localhost", "127.0.0.1", "::1"].includes(parsed.hostname);
  if (parsed.protocol !== "https:" && !(parsed.protocol === "http:" && localDevelopmentHost)) throw new Error("Use a secure HTTPS workspace address.");
  if (parsed.username || parsed.password) throw new Error("Workspace addresses cannot include credentials.");
  parsed.hash = "";
  parsed.search = "";
  return parsed.toString().replace(/\/$/, "");
}

function readJson<T>(filePath: string): T | null {
  try {
    return JSON.parse(fs.readFileSync(filePath, "utf8")) as T;
  } catch {
    return null;
  }
}

function readConfiguredServerUrl(): string {
  const saved = readJson<DesktopConfig>(settingsPath())?.serverUrl;
  if (saved) {
    try { return normalizeServerUrl(saved); } catch { return ""; }
  }
  const defaults = readJson<DesktopConfig>(path.join(__dirname, "default-config.json"))?.serverUrl;
  if (defaults) {
    try { return normalizeServerUrl(defaults); } catch { return ""; }
  }
  return "";
}

function saveConfiguredServerUrl(serverUrl: string): void {
  const directory = path.dirname(settingsPath());
  fs.mkdirSync(directory, { recursive: true });
  const temporaryPath = `${settingsPath()}.tmp`;
  fs.writeFileSync(temporaryPath, `${JSON.stringify({ serverUrl }, null, 2)}\n`, "utf8");
  fs.renameSync(temporaryPath, settingsPath());
}

async function testConnection(rawUrl: unknown): Promise<ConnectionResult> {
  let serverUrl: string;
  try {
    serverUrl = normalizeServerUrl(rawUrl);
  } catch (error) {
    return { ok: false, message: error instanceof Error ? error.message : "Enter a valid workspace address." };
  }

  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), 10_000);
  try {
    const response = await fetch(`${serverUrl}/api/v1/healthz/`, {
      headers: { Accept: "application/json" },
      signal: controller.signal,
    });
    if (!response.ok) return { ok: false, message: `The workspace responded with ${response.status}. Ask your setup partner to check it.` };
    return { ok: true, url: serverUrl, message: "Connected. Project Hope is ready." };
  } catch {
    return { ok: false, message: "We could not reach that workspace. Check the address or ask your setup partner." };
  } finally {
    clearTimeout(timeout);
  }
}

function isAllowedWorkspaceUrl(value: string): boolean {
  if (!activeServerUrl) return false;
  try { return new URL(value).origin === new URL(activeServerUrl).origin; } catch { return false; }
}

function showSetup(message = ""): void {
  if (!mainWindow || mainWindow.isDestroyed()) return;
  void mainWindow.loadFile(path.join(__dirname, "../assets/setup.html"), { query: { message } });
}

function openWorkspace(serverUrl: string): void {
  activeServerUrl = serverUrl;
  void mainWindow?.loadURL(serverUrl);
}

function createWindow(): BrowserWindow {
  const window = new BrowserWindow({
    width: 1440,
    height: 920,
    minWidth: 960,
    minHeight: 680,
    show: false,
    backgroundColor: "#f4f0e8",
    title: "Project Hope",
    webPreferences: {
      contextIsolation: true,
      nodeIntegration: false,
      sandbox: true,
      preload: path.join(__dirname, "preload.js"),
    },
  });

  window.once("ready-to-show", () => window.show());
  window.webContents.setWindowOpenHandler(({ url }) => {
    if (isAllowedWorkspaceUrl(url)) return { action: "allow" };
    void shell.openExternal(url);
    return { action: "deny" };
  });
  window.webContents.on("will-navigate", (event, url) => {
    if (!url.startsWith("file://") && !isAllowedWorkspaceUrl(url)) {
      event.preventDefault();
      void shell.openExternal(url);
    }
  });
  window.webContents.on("did-fail-load", (_event, errorCode) => {
    if (errorCode !== -3) showSetup("We could not open the workspace. You can check the address and try again.");
  });
  window.on("closed", () => {
    mainWindow = null;
  });
  return window;
}

function registerIpc(): void {
  ipcMain.handle("get-config", () => ({
    serverUrl: activeServerUrl || readConfiguredServerUrl(),
    version: app.getVersion(),
  }));
  ipcMain.handle("test-connection", (_event, serverUrl: unknown) => testConnection(serverUrl));
  ipcMain.handle("save-server-url", async (_event, serverUrl: unknown) => {
    const result = await testConnection(serverUrl);
    if (!result.ok || !result.url) return result;
    saveConfiguredServerUrl(result.url);
    openWorkspace(result.url);
    return result;
  });
}

const gotSingleInstanceLock = app.requestSingleInstanceLock();
if (!gotSingleInstanceLock) {
  app.quit();
} else {
  app.on("second-instance", () => mainWindow?.show());
  app.whenReady().then(() => {
    registerIpc();
    mainWindow = createWindow();
    const configuredUrl = readConfiguredServerUrl();
    if (configuredUrl) openWorkspace(configuredUrl);
    else showSetup();

    if (app.isPackaged) {
      autoUpdater.checkForUpdatesAndNotify().catch(() => undefined);
    }
    app.on("activate", () => {
      if (BrowserWindow.getAllWindows().length === 0) mainWindow = createWindow();
    });
  });
  app.on("window-all-closed", () => {
    if (process.platform !== "darwin") app.quit();
  });
}
