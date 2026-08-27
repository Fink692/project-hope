import manifest from "./release-manifest.json";

export const release = manifest;
export type Platform = "windows" | "mac" | "linux";

export const platforms: { id: Platform; title: string; format: string; note: string; file: string }[] = [
  { id: "windows", title: "Windows", format: "Windows 10 / 11 · 64-bit", file: "Project-Hope-" + release.version + "-win-x64.exe", note: "Run the installer, then open Project Hope from your Start menu." },
  { id: "mac", title: "macOS", format: "Apple silicon · M-series", file: "Project-Hope-" + release.version + "-mac-arm64.dmg", note: "Open the disk image and move Project Hope to Applications. Not for Intel Macs." },
  { id: "linux", title: "Linux", format: "x86-64 · AppImage", file: "Project-Hope-" + release.version + "-linux-x86_64.AppImage", note: "Make the AppImage executable, then open it. A Debian package is also available." },
];

export function getAsset(filename: string) {
  return release.assets.find((asset) => asset.file === filename);
}
export function downloadPath(filename: string) {
  return "/downloads/" + encodeURIComponent(filename);
}
export function displaySize(bytes: number) {
  return (bytes / 1024 / 1024).toFixed(1) + " MB";
}
