# Project Hope 1.8 accessibility evidence

- Date: 2026-08-23
- Scope: CRM contact list/correction, guided spreadsheet preview and import, owner-only export, viewer restrictions, and reviewed duplicate merges
- Target: WCAG 2.2 Level AA engineering baseline

This is engineering evidence, not a legal certification or a substitute for testing with people who use assistive technology.

## Automated result

The Vitest suite runs axe-core 4.13.0 with the `wcag2a`, `wcag2aa`, `wcag21a`, `wcag21aa`, and `wcag22aa` rule tags. The complete reviewed-import journey reports zero automated violations and is part of a 21-test web and shared-client interaction suite.

The tests verify a labelled file picker; named CRM navigation; semantic preview heading and summary terms; a captioned row-review table; per-row action labels; text descriptions for new, matched, possible-duplicate, and invalid states; disabled invalid actions; error messages that identify the field and correction; a text import count; explicit duplicate confirmation; editor correction; and viewer-only controls. Multipart requests are also checked to ensure the browser supplies its safe content boundary. Color contrast remains excluded from jsdom because it cannot calculate painted backgrounds reliably; the shared palette retains the browser-assisted contrast evidence recorded in `accessibility-audit-v1.5.md`.

## Interaction review

- The migration is presented as Choose, Review, Finish and explains that previewing does not change records.
- Status never relies on color alone; every state has a visible text label and invalid rows include field-specific text.
- Native file, select, checkbox, and button controls remain keyboard operable and retain visible focus treatment.
- Wide review data is contained in a horizontally scrollable region at narrow widths; surrounding actions stack without page-level horizontal overflow.
- Busy, disabled, error, completion, and merge states have text and appropriate live-region or alert behavior.
- Bulk import, export, and duplicate controls are absent for viewers; read-only status is explained in text.
- Duplicate merging requires both a selected primary contact and an explicit reviewed-pair checkbox.

## Remaining external gate

Before claiming WCAG 2.2 AA conformance for a deployed service, complete keyboard-only and 200%/400% zoom checks plus current NVDA/Firefox or Chrome, VoiceOver/Safari, and supported mobile screen-reader journeys. Include a large preview table, invalid and duplicate rows, file-picker errors, an expired preview, merge blocks, CSV/XLSX downloads, and correction loops with representative charity users, including people with cognitive, vision, and motor disabilities.
