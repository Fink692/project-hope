import { describe, expect, it, vi } from "vitest";

import {
  ContactImportPreview,
  HopeApiClient,
} from "../../../packages/api-client/src/index";

const preview: ContactImportPreview = {
  schemaVersion: 1,
  fileName: "contacts.csv",
  fileType: "csv",
  fileSha256: "a".repeat(64),
  columns: ["first_name", "email"],
  summary: {
    totalRows: 1,
    newRecords: 1,
    exactMatches: 0,
    possibleDuplicates: 0,
    invalidRows: 0,
  },
  warnings: [],
  rows: [],
  expiresInSeconds: 900,
  previewToken: "signed-preview",
};

function jsonResponse(body: unknown, status = 200) {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

describe("HopeApiClient CRM migration", () => {
  it("uploads previews as multipart without overriding the boundary", async () => {
    const fetcher = vi.fn<typeof fetch>().mockResolvedValue(jsonResponse(preview));
    const client = new HopeApiClient("https://hope.example/api/v1/", fetcher, "secret");
    const file = new File(["first_name,email\nAmina,amina@example.org"], "contacts.csv", {
      type: "text/csv",
    });

    await expect(client.previewContactImport("north star", file)).resolves.toEqual(preview);

    const [url, init] = fetcher.mock.calls[0];
    const headers = new Headers(init?.headers);
    expect(url).toBe("https://hope.example/api/v1/organizations/north%20star/crm/imports/preview/");
    expect(init?.method).toBe("POST");
    expect(headers.get("Authorization")).toBe("Token secret");
    expect(headers.has("Content-Type")).toBe(false);
    expect((init?.body as FormData).get("file")).toBeInstanceOf(File);
  });

  it("commits only the reviewed row actions with the same file", async () => {
    const result = {
      created: 1,
      updated: 0,
      unchanged: 0,
      skipped: 1,
      invalid: 0,
      createdIds: ["contact-1"],
      updatedIds: [],
      fileSha256: "a".repeat(64),
    };
    const fetcher = vi.fn<typeof fetch>().mockResolvedValue(jsonResponse(result, 201));
    const client = new HopeApiClient("/api/v1", fetcher);
    const file = new File(["first_name\nAmina"], "contacts.csv", { type: "text/csv" });
    const actions = [
      { rowNumber: 2, action: "create" as const },
      { rowNumber: 3, action: "skip" as const },
    ];

    await expect(
      client.commitContactImport("north-star", file, "signed-preview", actions),
    ).resolves.toEqual(result);

    const form = fetcher.mock.calls[0][1]?.body as FormData;
    expect(form.get("previewToken")).toBe("signed-preview");
    expect(JSON.parse(String(form.get("actions")))).toEqual(actions);
    expect(form.get("file")).toBeInstanceOf(File);
  });

  it("returns a safe filename and blob for portable exports", async () => {
    const fetcher = vi.fn<typeof fetch>().mockResolvedValue(
      new Response("first_name\nAmina", {
        headers: {
          "Content-Disposition": "attachment; filename*=UTF-8''project%20hope.csv",
          "Content-Type": "text/csv; charset=utf-8",
        },
      }),
    );
    const client = new HopeApiClient("/api/v1", fetcher);

    const downloaded = await client.exportContacts("north-star", {
      fileFormat: "csv",
      includeMerged: true,
    });

    expect(fetcher.mock.calls[0][0]).toBe(
      "/api/v1/organizations/north-star/crm/export/?fileFormat=csv&includeMerged=true",
    );
    expect(downloaded.filename).toBe("project hope.csv");
    expect(downloaded.contentType).toBe("text/csv; charset=utf-8");
    expect(await downloaded.blob.text()).toContain("Amina");
  });

  it("surfaces plain-text service errors instead of hiding them", async () => {
    const fetcher = vi
      .fn<typeof fetch>()
      .mockResolvedValue(new Response("Upload temporarily unavailable", { status: 503 }));
    const client = new HopeApiClient("/api/v1", fetcher);

    await expect(client.getContactDuplicates("north-star")).rejects.toThrow(
      "Upload temporarily unavailable",
    );
  });
});
