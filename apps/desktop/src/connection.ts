export function normalizeServerUrl(value: unknown): string {
  if (typeof value !== "string" || !value.trim()) throw new Error("Enter your charity workspace web address, or open the sample workspace.");
  const text = value.trim();
  if (!text.includes("://") && text.includes("@")) throw new Error("That is an email address. This field needs your workspace website; you sign in with email after connecting.");
  let parsed: URL;
  try { parsed = new URL(text); } catch { throw new Error("Enter the full workspace web address, starting with https://."); }
  const local = ["localhost", "127.0.0.1", "[::1]"].includes(parsed.hostname);
  if (parsed.protocol !== "https:" && !(parsed.protocol === "http:" && local)) throw new Error("Use a secure HTTPS workspace address.");
  if (parsed.username || parsed.password || parsed.search || parsed.hash) throw new Error("Use the workspace address without passwords, query parameters, or a fragment.");
  return parsed.toString().replace(/\/$/, "");
}

export function isExternalWebUrl(value: string): boolean {
  try {
    const url = new URL(value);
    return ["https:", "http:"].includes(url.protocol) && !url.username && !url.password;
  } catch { return false; }
}

export function isRuntimeOrigin(value: unknown): value is string {
  if (typeof value !== "string") return false;
  try {
    const url = new URL(value);
    return url.protocol === "http:" && url.hostname === "127.0.0.1" && !!url.port
      && url.origin === value && !url.username && !url.password;
  } catch { return false; }
}
