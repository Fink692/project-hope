import { app, BrowserWindow, ipcMain, Menu, shell, type IpcMainInvokeEvent } from "electron";
import { autoUpdater } from "electron-updater";
import fs from "node:fs";
import path from "node:path";
import { pathToFileURL } from "node:url";
import { normalizeServerUrl, isExternalWebUrl } from "./connection";
import { ShowcaseRuntime } from "./runtime";

type DesktopConfig = { serverUrl?: string; mode?: "showcase" | "connected" };
type ConnectionResult = { ok: boolean; url?: string; message: string };
const setupPath = path.join(__dirname, "../assets/setup.html");
const setupUrl = pathToFileURL(setupPath).href;
const settingsPath = () => path.join(app.getPath("userData"), "settings.json");
let mainWindow: BrowserWindow | null = null;
let activeServerUrl = "";
let runtime: ShowcaseRuntime;
let quitting = false;

if (process.env.PROJECT_HOPE_DESKTOP_PROFILE) app.setPath("userData", path.resolve(process.env.PROJECT_HOPE_DESKTOP_PROFILE));

function readJson<T>(filePath: string): T | null {
  try { return JSON.parse(fs.readFileSync(filePath, "utf8")) as T; } catch { return null; }
}

function readConfig(): DesktopConfig {
  const saved = readJson<DesktopConfig>(settingsPath());
  if (saved?.mode === "showcase") return { mode: "showcase" };
  const url = saved?.serverUrl || readJson<DesktopConfig>(path.join(__dirname, "default-config.json"))?.serverUrl;
  if (url) {
    try { return { mode: "connected", serverUrl: normalizeServerUrl(url) }; } catch { /* Keep saved settings available for recovery. */ }
  }
  return { mode: "showcase" };
}

function saveConfig(config: DesktopConfig): void {
  fs.mkdirSync(path.dirname(settingsPath()), { recursive: true });
  const temporary = `${settingsPath()}.tmp`;
  fs.writeFileSync(temporary, `${JSON.stringify(config, null, 2)}\n`, { encoding: "utf8", mode: 0o600 });
  fs.renameSync(temporary, settingsPath());
}

async function testConnection(rawUrl: unknown): Promise<ConnectionResult> {
  let serverUrl: string;
  try { serverUrl = normalizeServerUrl(rawUrl); } catch (error) {
    return { ok: false, message: error instanceof Error ? error.message : "Enter a valid workspace web address." };
  }
  try {
    const response = await fetch(`${serverUrl}/api/v1/healthz/`, { headers: { Accept: "application/json" }, signal: AbortSignal.timeout(10_000), redirect: "error" });
    const body = await response.json();
    if (!response.ok || body?.service !== "project-hope-core" || body?.status !== "ok" || body?.database !== "ok") return { ok: false, message: "That address is not a healthy Project Hope workspace. Check the web address with your coordinator." };
    return { ok: true, url: serverUrl, message: "Connected. Your charity sign-in is ready." };
  } catch {
    return { ok: false, message: "We could not reach that workspace. Check the address, or use the sample workspace while your team gets connected." };
  }
}

function isAllowedWorkspaceUrl(value: string): boolean {
  try { return !!activeServerUrl && new URL(value).origin === new URL(activeServerUrl).origin; } catch { return false; }
}

function showSetup(message = ""): void {
  if (!mainWindow || mainWindow.isDestroyed()) return;
  void mainWindow.loadFile(setupPath, { query: { message } });
}

async function openShowcase(): Promise<ConnectionResult> {
  try {
    mainWindow?.webContents.send("runtime-status", "Preparing your sample workspace… The first launch may take a moment.");
    const origin = await runtime.start();
    activeServerUrl = origin;
    saveConfig({ mode: "showcase" });
    await mainWindow?.loadURL(`${origin}/desktop/start/`);
    return { ok: true, message: "Sample workspace ready." };
  } catch (error) {
    const message = error instanceof Error ? error.message : "The sample workspace could not open.";
    showSetup(message);
    return { ok: false, message };
  }
}

function requireSetup(event: IpcMainInvokeEvent): void {
  if (event.sender !== mainWindow?.webContents || event.senderFrame !== event.sender.mainFrame || event.senderFrame.url.split("?")[0] !== setupUrl) throw new Error("Open workspace settings from the Project Hope menu.");
}

function registerIpc(): void {
  ipcMain.handle("get-config", (event) => { requireSetup(event); return { ...readConfig(), version: app.getVersion() }; });
  ipcMain.handle("start-showcase", (event) => { requireSetup(event); return openShowcase(); });
  ipcMain.handle("save-server-url", async (event, value: unknown) => {
    requireSetup(event);
    const result = await testConnection(value);
    if (!result.ok || !result.url) return result;
    saveConfig({ mode: "connected", serverUrl: result.url });
    runtime.stop();
    activeServerUrl = result.url;
    await mainWindow?.loadURL(result.url);
    return result;
  });
  ipcMain.handle("show-setup", (event) => {
    if (event.sender === mainWindow?.webContents && event.senderFrame === event.sender.mainFrame && isAllowedWorkspaceUrl(event.senderFrame.url)) showSetup();
  });
}

function createWindow(): BrowserWindow {
  const window = new BrowserWindow({
    width: 1440, height: 960, minWidth: 960, minHeight: 680, show: false,
    backgroundColor: "#f4f0e8", title: "Project Hope", icon: path.join(__dirname, "../assets/icon.png"),
    webPreferences: { contextIsolation: true, nodeIntegration: false, sandbox: true, preload: path.join(__dirname, "preload.js") },
  });
  window.once("ready-to-show", () => window.show());
  window.webContents.session.setPermissionRequestHandler((_contents, _permission, callback) => callback(false));
  window.webContents.session.setPermissionCheckHandler(() => false);
  window.webContents.session.webRequest.onBeforeSendHeaders((details, callback) => {
    const headers = { ...details.requestHeaders };
    for (const key of Object.keys(headers)) if (key.toLowerCase() === "x-project-hope-desktop-token") delete headers[key];
    if (runtime?.origin && activeServerUrl === runtime.origin && new URL(details.url).origin === runtime.origin && details.webContentsId === window.webContents.id) headers["X-Project-Hope-Desktop-Token"] = runtime.token;
    callback({ requestHeaders: headers });
  });
  const external = (url: string) => { if (isExternalWebUrl(url)) void shell.openExternal(url); };
  window.webContents.setWindowOpenHandler(({ url }) => { external(url); return { action: "deny" }; });
  window.webContents.on("will-navigate", (event, url) => {
    if (!isAllowedWorkspaceUrl(url) && url.split("?")[0] !== setupUrl) { event.preventDefault(); external(url); }
  });
  window.webContents.on("will-redirect", (event, url) => {
    if (!isAllowedWorkspaceUrl(url)) { event.preventDefault(); showSetup("The workspace redirected to a different website. Check its address with your coordinator."); }
  });
  window.webContents.on("did-fail-load", (_event, code, _description, url, isMainFrame) => {
    if (isMainFrame && code !== -3 && !url.startsWith(setupUrl)) showSetup("We could not open the workspace. You can retry or use the sample workspace.");
  });
  window.on("closed", () => { mainWindow = null; });
  return window;
}

if (!app.requestSingleInstanceLock()) app.quit();
else {
  app.on("second-instance", () => { mainWindow?.show(); mainWindow?.focus(); });
  app.whenReady().then(async () => {
    runtime = new ShowcaseRuntime({ appPath: app.getAppPath(), resourcesPath: process.resourcesPath, userData: app.getPath("userData"), packaged: app.isPackaged, onExit: () => { if (!quitting) showSetup("The sample workspace stopped. Select Open sample workspace to restart it; your sample edits are saved."); } });
    registerIpc();
    mainWindow = createWindow();
    Menu.setApplicationMenu(Menu.buildFromTemplate([
      ...(process.platform === "darwin" ? [{ role: "appMenu" as const }] : []),
      { label: "Project Hope", submenu: [{ label: "Switch workspace…", click: () => showSetup() }, { label: "Open sample workspace", click: () => { showSetup("Preparing your sample workspace…"); void openShowcase(); } }, { type: "separator" }, { role: "quit" }] },
      { role: "editMenu" }, { role: "viewMenu" },
      { label: "Help", submenu: [{ label: "Getting started", click: () => void shell.openExternal("https://project-hope-charities.vercel.app/guide") }] },
    ]));
    const config = readConfig();
    if (config.mode === "connected" && config.serverUrl) { activeServerUrl = config.serverUrl; void mainWindow.loadURL(config.serverUrl); }
    else { await mainWindow.loadFile(setupPath, { query: { message: "Preparing your sample workspace…" } }); void openShowcase(); }
    if (app.isPackaged) autoUpdater.checkForUpdatesAndNotify().catch(() => undefined);
    app.on("activate", () => { if (!mainWindow) { mainWindow = createWindow(); showSetup(); } });
  });
  app.on("before-quit", () => { quitting = true; runtime?.stop(); });
  app.on("window-all-closed", () => { if (process.platform !== "darwin") app.quit(); });
}
