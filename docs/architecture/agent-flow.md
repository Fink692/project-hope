# Bounded AI workflow design

AI was deferred from Phase 1. The current baseline implements the same bounded contract across the completed modules:

```text
User request
  -> intent/workflow router
  -> authentication, organization, programme, consent and policy checks
  -> permission-aware retrieval
  -> bounded task operation through AI gateway
  -> strict structured-output validation
  -> privacy, risk, citation and grounding checks
  -> human review when required
  -> deterministic approved action
  -> audit event
```

## Workflow state machine

```text
created -> classified -> awaiting_context -> retrieving -> generating
  -> validating -> awaiting_review -> approved -> executing -> completed

Any active state may move to failed or cancelled.
awaiting_review -> rejected is terminal for the proposed action.
```

Each workflow stores organization, user, workflow type, authorized scope, input references, retrieved source identifiers, prompt version, model/runtime, structured output, validation results, risk flags, approval, final action, and audit history.

## Gateway contract

The internal gateway exposes narrow operations such as:

- `POST /ai/v1/draft-email`
- `POST /ai/v1/answer-grant-question`
- `POST /ai/v1/extract-document`
- `POST /ai/v1/classify-intent`
- `POST /ai/v1/translate-segments`
- `POST /ai/v1/embed`
- `POST /ai/v1/transcribe`
- `POST /ai/v1/synthesize-speech`

Each operation declares a maximum context, approved retrieval collections, output schema, prohibited tasks, model policy, and review policy. Retrieved email, documents, web content, transcripts, and plugins are untrusted data and are delimited as data; they cannot alter system instructions, permissions, or available tools.

## Non-negotiable safety boundaries

No language model may send email, submit a grant, alter sensitive records, reject volunteers, decide service eligibility, prioritize vulnerable people, provide medical/legal/emergency/crisis advice, execute shell or SQL, install plugins, or grant permissions. Models produce drafts, recommendations, or analysis with provenance.
