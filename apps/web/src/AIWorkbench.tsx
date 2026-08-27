import { useState, type FormEvent } from "react";

type Result = { workflowId: string; state: string; output: Record<string, unknown>; riskFlags: string[]; modelIdentifier: string; runtime: string };
type Operation = "draft-email" | "classify-intent" | "translate-segments" | "transform-accessibility";
const operations: { id: Operation; label: string; sample: string }[] = [
  { id: "draft-email", label: "Draft a reply", sample: "Hello, I would like to volunteer at your community pantry on Saturdays. How do I get started? Thank you, Alex (fictional sample)." },
  { id: "classify-intent", label: "Understand a message", sample: "I would like to volunteer at the community pantry. Can someone tell me about the next orientation?" },
  { id: "translate-segments", label: "Translate a message", sample: "Thank you for volunteering. Your welcome appointment is on Saturday." },
  { id: "transform-accessibility", label: "Make it clearer", sample: "Individuals who wish to participate should commence the registration process approximately one week before the activity." },
];

export default function AIWorkbench({ organization, runRequest, initialOperation = "draft-email", canEdit }: {
  organization: { slug: string };
  runRequest: (path: string, init?: RequestInit) => Promise<unknown>;
  initialOperation?: Operation;
  canEdit: boolean;
}) {
  const [operation, setOperation] = useState<Operation>(initialOperation);
  const [text, setText] = useState("");
  const [subject, setSubject] = useState("Thank you for getting in touch");
  const [source, setSource] = useState("en");
  const [target, setTarget] = useState("fr");
  const [busy, setBusy] = useState(false);
  const [result, setResult] = useState<Result | null>(null);
  const [error, setError] = useState("");
  const [copied, setCopied] = useState(false);
  const selected = operations.find(({ id }) => id === operation)!;
  const output = result ? String(result.output.body ?? result.output.translatedText ?? result.output.transformedText ?? result.output.intent ?? "No text returned.") : "";

  async function generate(event: FormEvent) {
    event.preventDefault();
    if (!text.trim() || !canEdit) return;
    setBusy(true); setError(""); setResult(null); setCopied(false);
    const payload = operation === "draft-email" ? { subject, body: text }
      : operation === "translate-segments" ? { text, sourceLanguage: source, targetLanguage: target }
        : operation === "transform-accessibility" ? { text, transformType: "plain_language", sourceType: "manual" } : { text };
    try {
      const response = await runRequest(`/api/v1/organizations/${organization.slug}/ai/v1/${operation}/`, { method: "POST", body: JSON.stringify(payload), signal: AbortSignal.timeout(75_000) }) as Result;
      if (!response.workflowId || !response.output) throw new Error("The workspace returned an incomplete result. Please try again.");
      setResult(response);
    } catch (reason) { setError(reason instanceof Error ? reason.message : "The assistant could not finish. Your original text is unchanged."); }
    finally { setBusy(false); }
  }

  return <div className="ai-workbench">
    <p className="eyebrow">Assistance, with you in charge</p>
    <h3 className="module-title">A little help with the words.</h3>
    <p className="module-lede">Prepare a reply, understand an incoming message, translate, or make a notice easier to read. Every result stays a draft. Nothing is sent from here.</p>
    <div className="ai-choices" aria-label="Assistant tasks">{operations.map((item) => <button key={item.id} type="button" className={`button ${operation === item.id ? "primary" : "secondary"} compact`} aria-pressed={operation === item.id} disabled={busy} onClick={() => { setOperation(item.id); setResult(null); setError(""); }}>{item.label}</button>)}</div>
    {!canEdit && <p className="permission-note">You have view-only access. A teammate with editing access can create drafts.</p>}
    <form className="ai-input-form" onSubmit={generate}>
      {operation === "draft-email" && <label>Reply subject<input value={subject} onChange={(event) => setSubject(event.target.value)} maxLength={500} required /></label>}
      {operation === "translate-segments" && <div className="ai-languages"><label>From<select value={source} onChange={(event) => setSource(event.target.value)}><option value="en">English</option><option value="fr">French</option><option value="es">Spanish</option><option value="ar">Arabic</option></select></label><label>To<select value={target} onChange={(event) => setTarget(event.target.value)}><option value="fr">French</option><option value="en">English</option><option value="es">Spanish</option><option value="ar">Arabic</option></select></label></div>}
      <label>Original message<textarea rows={7} value={text} onChange={(event) => setText(event.target.value)} placeholder="Paste your message here, or try the sample below." maxLength={12000} required /></label>
      <div className="ai-actions"><button type="button" className="button secondary compact" disabled={busy} onClick={() => { setText(selected.sample); setResult(null); }}>Use a fictional sample</button><button type="submit" className="button primary compact" disabled={busy || !canEdit || !text.trim()} aria-busy={busy}>{busy ? "Preparing your draft…" : selected.label}</button></div>
    </form>
    {error && <p className="form-error" role="alert">{error}</p>}
    {result && <section className="ai-result" aria-labelledby="ai-result-title"><div className="ai-result-heading"><h4 id="ai-result-title">Ready for your review</h4><span>{result.runtime === "ollama" ? "Model-generated draft" : "Safety template · not generative AI"}</span></div>
      {result.runtime !== "ollama" && <p className="permission-note">A language model was not used for this result. The template or basic text rules are limited; translation may be incomplete. Connect a supported AI runtime for model-generated answers.</p>}
      <label>Draft result<textarea readOnly rows={8} value={output} dir={operation === "translate-segments" && target === "ar" ? "rtl" : "auto"} /></label>
      <p>Check accuracy, tone, and any important details before using this draft.</p>
      <div className="ai-actions"><small>Model: {result.modelIdentifier || "Safety adapter"} · Saved in your workflow history</small><button className="button secondary compact" type="button" onClick={async () => { try { await navigator.clipboard.writeText(output); setCopied(true); } catch { setError("Select the draft text and copy it using your keyboard."); } }}>{copied ? "Copied" : "Copy draft"}</button></div>
    </section>}
    <p className="ai-footnote">In the desktop sample, model-generated drafts use Ollama on this computer when its supported models are available. <a href="https://project-hope-charities.vercel.app/guide#ai" target="_blank" rel="noreferrer">About optional AI setup</a></p>
  </div>;
}
