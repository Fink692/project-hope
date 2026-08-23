export type Organization = { id: string; name: string; slug: string; status: string };
export type MfaStatus = { enabled: boolean; required: boolean; enrollmentRequired: boolean; enabledAt: string | null; recoveryCodesRemaining: number };
export type MfaChallengeResponse = { mfaRequired: true; challenge: string; expiresInSeconds: number; methods: Array<"totp" | "recovery_code"> };
export type LoginResponse = { user: { email: string; display_name: string }; token: string; mfa: MfaStatus } | MfaChallengeResponse;
export type SessionResponse = {
  user: { email: string; display_name: string };
  organizations: Array<{ organization: Organization; role: string; membershipId: string }>;
  mfa: MfaStatus;
  workspaceAccessGranted: boolean;
};
export type WorkflowState =
  | "created" | "classified" | "awaiting_context" | "retrieving" | "generating"
  | "validating" | "awaiting_review" | "approved" | "executing" | "completed"
  | "rejected" | "failed" | "cancelled";
export type WorkflowResult = {
  workflowId: string;
  state: WorkflowState;
  output: Record<string, unknown>;
  riskFlags: string[];
};

export class HopeApiClient {
  constructor(
    private readonly baseUrl: string,
    private readonly fetcher: typeof fetch = fetch,
    private readonly token?: string,
  ) {}

  withToken(token: string) {
    return new HopeApiClient(this.baseUrl, this.fetcher, token);
  }

  private async request<T>(path: string, init: RequestInit = {}) {
    const headers = new Headers(init.headers);
    headers.set("Accept", "application/json");
    if (this.token) headers.set("Authorization", "Token " + this.token);
    if (init.method && init.method !== "GET" && !this.token && typeof document !== "undefined") {
      const csrf = document.cookie.split("; ").find((row) => row.startsWith("csrftoken="))?.split("=")[1];
      if (csrf) headers.set("X-CSRFToken", decodeURIComponent(csrf));
    }
    const response = await this.fetcher(this.baseUrl.replace(/\/+$/, "") + path, {
      ...init,
      credentials: "include",
      headers,
    });
    const body = await response.json().catch(() => ({}));
    if (!response.ok) {
      const fieldErrors = body && typeof body === "object"
        ? Object.entries(body as Record<string, unknown>)
          .filter(([key]) => key !== "detail")
          .map(([key, value]) => key + ": " + (Array.isArray(value) ? value.join(", ") : String(value)))
          .join(" · ")
        : "";
      throw new Error(body?.detail || fieldErrors || (init.method ?? "GET") + " " + path + " failed");
    }
    return body as T;
  }

  async get<T>(path: string): Promise<T> {
    return this.request<T>(path);
  }

  async post<T>(path: string, payload: Record<string, unknown>): Promise<T> {
    return this.request<T>(path, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
  }
}
