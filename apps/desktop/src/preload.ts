import { contextBridge, ipcRenderer } from "electron";

contextBridge.exposeInMainWorld("projectHopeDesktop", {
  getConfig: () => ipcRenderer.invoke("get-config"),
  testConnection: (serverUrl: string) => ipcRenderer.invoke("test-connection", serverUrl),
  saveServerUrl: (serverUrl: string) => ipcRenderer.invoke("save-server-url", serverUrl),
});
