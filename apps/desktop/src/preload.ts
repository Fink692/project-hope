import { contextBridge, ipcRenderer } from "electron";

contextBridge.exposeInMainWorld("projectHopeDesktop", {
  getConfig: () => ipcRenderer.invoke("get-config"),
  saveServerUrl: (serverUrl: string) => ipcRenderer.invoke("save-server-url", serverUrl),
  startShowcase: () => ipcRenderer.invoke("start-showcase"),
  showSetup: () => ipcRenderer.invoke("show-setup"),
  onRuntimeStatus: (callback: (message: string) => void) => {
    const listener = (_event: Electron.IpcRendererEvent, message: string) => callback(message);
    ipcRenderer.on("runtime-status", listener);
    return () => ipcRenderer.removeListener("runtime-status", listener);
  },
});
