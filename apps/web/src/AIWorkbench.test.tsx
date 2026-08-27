import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import AIWorkbench from "./AIWorkbench";

afterEach(cleanup);
describe("Reviewable AI workbench", () => {
  it("uses the real tenant endpoint and labels model output as a draft", async () => {
    const request = vi.fn().mockResolvedValue({ workflowId: "workflow-1", state: "awaiting_review", runtime: "ollama", modelIdentifier: "qwen3:4b", output: { body: "Thank you for offering to volunteer." }, riskFlags: ["human_approval_required"] });
    render(<AIWorkbench organization={{ slug: "hope-demo" }} runRequest={request} canEdit />);
    fireEvent.click(screen.getByRole("button", { name: "Use a fictional sample" }));
    fireEvent.submit(screen.getByLabelText("Original message").closest("form")!);
    expect(await screen.findByText("Model-generated draft")).toBeInTheDocument();
    expect(screen.getByLabelText("Draft result")).toHaveValue("Thank you for offering to volunteer.");
    expect(request.mock.calls[0][0]).toBe("/api/v1/organizations/hope-demo/ai/v1/draft-email/");
    expect(JSON.parse(request.mock.calls[0][1].body).body).toContain("fictional sample");
    expect(screen.queryByRole("button", { name: /^send/i })).not.toBeInTheDocument();
  });
  it("does not claim a deterministic template is generative AI", async () => {
    const request = vi.fn().mockResolvedValue({ workflowId: "workflow-2", state: "awaiting_review", runtime: "deterministic", modelIdentifier: "deterministic-local-adapter-v1", output: { translatedText: "bonjour" }, riskFlags: [] });
    render(<AIWorkbench organization={{ slug: "hope-demo" }} runRequest={request} canEdit initialOperation="translate-segments" />);
    fireEvent.click(screen.getByRole("button", { name: "Use a fictional sample" }));
    fireEvent.submit(screen.getByLabelText("Original message").closest("form")!);
    expect(await screen.findByText("Safety template · not generative AI")).toBeInTheDocument();
    expect(screen.getByText(/translation may be incomplete/)).toBeInTheDocument();
  });
  it("keeps the original message after an error and blocks view-only generation", async () => {
    const request = vi.fn();
    render(<AIWorkbench organization={{ slug: "hope-demo" }} runRequest={request} canEdit={false} />);
    fireEvent.click(screen.getByRole("button", { name: "Use a fictional sample" }));
    fireEvent.submit(screen.getByLabelText("Original message").closest("form")!);
    expect(request).not.toHaveBeenCalled();
    expect(screen.getByText(/view-only access/)).toBeInTheDocument();
  });
  it("shows a request failure without inventing an answer", async () => {
    const request = vi.fn().mockRejectedValue(new Error("Workspace unavailable"));
    render(<AIWorkbench organization={{ slug: "hope-demo" }} runRequest={request} canEdit />);
    fireEvent.change(screen.getByLabelText("Original message"), { target: { value: "My original message" } });
    fireEvent.submit(screen.getByLabelText("Original message").closest("form")!);
    expect(await screen.findByRole("alert")).toHaveTextContent("Workspace unavailable");
    expect(screen.getByLabelText("Original message")).toHaveValue("My original message");
    expect(screen.queryByLabelText("Draft result")).not.toBeInTheDocument();
  });
});
