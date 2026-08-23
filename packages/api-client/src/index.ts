export type Organization = { id: string; name: string; slug: string; status: string };
export type MfaStatus = {
  enabled: boolean;
  required: boolean;
  enrollmentRequired: boolean;
  enabledAt: string | null;
  recoveryCodesRemaining: number;
};
export type MfaChallengeResponse = {
  mfaRequired: true;
  challenge: string;
  expiresInSeconds: number;
  methods: Array<"totp" | "recovery_code">;
};
export type LoginResponse =
  | { user: { email: string; display_name: string }; token: string; mfa: MfaStatus }
  | MfaChallengeResponse;
export type SessionResponse = {
  user: { email: string; display_name: string };
  organizations: Array<{
    organization: Organization;
    role: string;
    membershipId: string;
  }>;
  mfa: MfaStatus;
  workspaceAccessGranted: boolean;
};
export type WorkflowState =
  | "created"
  | "classified"
  | "awaiting_context"
  | "retrieving"
  | "generating"
  | "validating"
  | "awaiting_review"
  | "approved"
  | "executing"
  | "completed"
  | "rejected"
  | "failed"
  | "cancelled";
export type WorkflowResult = {
  workflowId: string;
  state: WorkflowState;
  output: Record<string, unknown>;
  riskFlags: string[];
};

export type ContactFileFormat = "xlsx" | "csv";
export type ContactCandidate = {
  id: string;
  displayName: string;
  contactType: string;
  firstName: string;
  lastName: string;
  organizationName: string;
  email: string;
  phone: string;
  externalRef: string;
  sensitivity: string;
  consentStatus: string;
  updatedAt: string;
  matchReasons: string[];
};
export type ContactImportRow = {
  rowNumber: number;
  status: "new" | "exact_match" | "possible_duplicate" | "invalid";
  values: Record<string, string>;
  providedFields: string[];
  errors: Record<string, string[]>;
  candidates: ContactCandidate[];
  recommendedAction: "create" | "skip";
};
export type ContactImportPreview = {
  schemaVersion: number;
  fileName: string;
  fileType: "csv" | "xlsx";
  fileSha256: string;
  columns: string[];
  summary: {
    totalRows: number;
    newRecords: number;
    exactMatches: number;
    possibleDuplicates: number;
    invalidRows: number;
  };
  warnings: string[];
  rows: ContactImportRow[];
  expiresInSeconds: number;
  previewToken: string;
};
export type ContactImportAction =
  | { rowNumber: number; action: "create" | "skip" }
  | { rowNumber: number; action: "update"; targetContactId: string };
export type ContactImportResult = {
  created: number;
  updated: number;
  unchanged: number;
  skipped: number;
  invalid: number;
  createdIds: string[];
  updatedIds: string[];
  fileSha256: string;
};
export type ContactDuplicatePair = {
  first: ContactCandidate;
  second: ContactCandidate;
  matchReasons: string[];
  confidence: "exact" | "strong" | "possible";
};
export type ContactDuplicateReview = {
  totalActiveContacts: number;
  totalCandidates: number;
  results: ContactDuplicatePair[];
};
export type ContactMergeResult = {
  primary: ContactCandidate;
  mergedContactId: string;
  reassigned: Record<string, number>;
  preserved: true;
};
export type FileDownload = {
  blob: Blob;
  filename: string;
  contentType: string;
};

function errorMessage(body: unknown, method: string, path: string): string {
  if (body && typeof body === "object") {
    const record = body as Record<string, unknown>;
    if (typeof record.detail === "string" && record.detail) return record.detail;
    const fieldErrors = Object.entries(record)
      .filter(([key]) => key !== "detail")
      .map(([key, value]) =>
        `${key}: ${Array.isArray(value) ? value.join(", ") : String(value)}`,
      )
      .join(" · ");
    if (fieldErrors) return fieldErrors;
  }
  return `${method} ${path} failed`;
}

function safeDownloadName(disposition: string, fallback: string): string {
  const encoded = disposition.match(/filename\*=UTF-8''([^;]+)/i)?.[1];
  const plain = disposition.match(/filename="?([^";]+)"?/i)?.[1];
  let suggested = plain ?? fallback;
  if (encoded) {
    try {
      suggested = decodeURIComponent(encoded.replace(/^"|"$/g, ""));
    } catch {
      suggested = fallback;
    }
  }
  return suggested.replace(/[\\/:*?"<>|\u0000-\u001f]/g, "-").slice(0, 180) || fallback;
}

export class HopeApiClient {
  constructor(
    private readonly baseUrl: string,
    private readonly fetcher: typeof fetch = fetch,
    private readonly token?: string,
  ) {}

  withToken(token: string) {
    return new HopeApiClient(this.baseUrl, this.fetcher, token);
  }

  private organizationPath(slug: string, suffix: string): string {
    return `/organizations/${encodeURIComponent(slug)}/${suffix.replace(/^\/+/, "")}`;
  }

  private async response(
    path: string,
    init: RequestInit = {},
    accept = "application/json",
  ) {
    const headers = new Headers(init.headers);
    headers.set("Accept", accept);
    if (this.token) headers.set("Authorization", `Token ${this.token}`);
    const method = (init.method ?? "GET").toUpperCase();
    if (
      !["GET", "HEAD", "OPTIONS"].includes(method) &&
      !this.token &&
      typeof document !== "undefined"
    ) {
      const csrf = document.cookie
        .split("; ")
        .find((row) => row.startsWith("csrftoken="))
        ?.split("=")[1];
      if (csrf) headers.set("X-CSRFToken", decodeURIComponent(csrf));
    }
    const response = await this.fetcher(this.baseUrl.replace(/\/+$/, "") + path, {
      ...init,
      credentials: "include",
      headers,
    });
    if (!response.ok) {
      const fallbackResponse = response.clone();
      const body = await response.json().catch(async () => {
        const text = await fallbackResponse.text().catch(() => "");
        return text ? { detail: text } : {};
      });
      throw new Error(errorMessage(body, method, path));
    }
    return response;
  }

  private async request<T>(path: string, init: RequestInit = {}): Promise<T> {
    const response = await this.response(path, init);
    return (await response.json().catch(() => ({}))) as T;
  }

  private multipartFile(file: Blob, fileName?: string): FormData {
    const form = new FormData();
    const inferredName =
      "name" in file && typeof file.name === "string" ? file.name : undefined;
    form.append("file", file, fileName ?? inferredName ?? "contacts.xlsx");
    return form;
  }

  private async download(path: string, fallbackName: string): Promise<FileDownload> {
    const response = await this.response(path, {}, "*/*");
    return {
      blob: await response.blob(),
      filename: safeDownloadName(
        response.headers.get("Content-Disposition") ?? "",
        fallbackName,
      ),
      contentType:
        response.headers.get("Content-Type") ?? "application/octet-stream",
    };
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

  async patch<T>(path: string, payload: Record<string, unknown>): Promise<T> {
    return this.request<T>(path, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
  }

  async previewContactImport(
    organizationSlug: string,
    file: Blob,
    fileName?: string,
  ): Promise<ContactImportPreview> {
    return this.request<ContactImportPreview>(
      this.organizationPath(organizationSlug, "crm/imports/preview/"),
      { method: "POST", body: this.multipartFile(file, fileName) },
    );
  }

  async commitContactImport(
    organizationSlug: string,
    file: Blob,
    previewToken: string,
    actions: ContactImportAction[],
    fileName?: string,
  ): Promise<ContactImportResult> {
    const form = this.multipartFile(file, fileName);
    form.append("previewToken", previewToken);
    form.append("actions", JSON.stringify(actions));
    return this.request<ContactImportResult>(
      this.organizationPath(organizationSlug, "crm/imports/commit/"),
      { method: "POST", body: form },
    );
  }

  async downloadContactTemplate(
    organizationSlug: string,
    fileFormat: ContactFileFormat = "xlsx",
  ): Promise<FileDownload> {
    const path = this.organizationPath(
      organizationSlug,
      `crm/template/?fileFormat=${encodeURIComponent(fileFormat)}`,
    );
    return this.download(path, `project-hope-contact-template.${fileFormat}`);
  }

  async exportContacts(
    organizationSlug: string,
    options: { fileFormat?: ContactFileFormat; includeMerged?: boolean } = {},
  ): Promise<FileDownload> {
    const fileFormat = options.fileFormat ?? "xlsx";
    const query = new URLSearchParams({
      fileFormat,
      includeMerged: String(options.includeMerged ?? false),
    });
    const path = this.organizationPath(organizationSlug, `crm/export/?${query}`);
    return this.download(path, `project-hope-contacts.${fileFormat}`);
  }

  async getContactDuplicates(
    organizationSlug: string,
    limit = 100,
  ): Promise<ContactDuplicateReview> {
    const safeLimit = Math.max(1, Math.min(Math.trunc(limit), 250));
    return this.get<ContactDuplicateReview>(
      this.organizationPath(organizationSlug, `crm/duplicates/?limit=${safeLimit}`),
    );
  }

  async mergeContacts(
    organizationSlug: string,
    primaryContactId: string,
    duplicateContactId: string,
  ): Promise<ContactMergeResult> {
    return this.post<ContactMergeResult>(
      this.organizationPath(organizationSlug, "crm/duplicates/merge/"),
      { primaryContactId, duplicateContactId, confirm: true },
    );
  }
}
