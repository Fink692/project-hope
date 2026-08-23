# Project Hope 1.6 accessibility evidence

- Date: 2026-08-23
- Scope: public journey, secure invitation acceptance, password recovery, and authenticated Team & access workspace
- Target: WCAG 2.2 Level AA engineering baseline

This is engineering evidence, not a legal certification or a substitute for testing with people who use assistive technology.

## Automated result

The Vitest suite runs axe-core 4.13.0 with the `wcag2a`, `wcag2aa`, `wcag21a`, `wcag21aa`, and `wcag22aa` rule tags. The public, invitation, and Team & access renders report zero automated violations. Color contrast is excluded from jsdom runs because jsdom does not calculate painted backgrounds reliably; the browser-assisted contrast evidence in `accessibility-audit-v1.5.md` still covers the unchanged shared palette.

The complete web suite contains 11 passing interaction journeys. It verifies semantic headings, named navigation, labelled form controls, live status/error regions, private credentials being consumed only from fragments and removed from browser history before render, protected owner controls, account recovery, and responsive production compilation.

## Browser-assisted review

- Live invitation and Team & access screens were rendered at 1440 × 1000 against a migrated temporary database and inspected from captured browser output.
- Invitation inputs use visible labels, native password semantics, a clear primary action, and a non-destructive cancel action.
- Team controls expose descriptive accessible names such as “Role for Amina Hope”; controls that an administrator may not use are disabled, and owner-only invitation actions are not exposed to administrators.
- Status and error text is not communicated by color alone.
- Existing visible-focus and reduced-motion rules apply to the new controls.

## Remaining external gate

Before claiming WCAG 2.2 AA conformance for a deployed service, complete keyboard-only and 200%/400% zoom checks plus current NVDA/Firefox or Chrome, VoiceOver/Safari, and supported mobile screen-reader journeys. Include expired invitation, weak-password, SMTP-delay, recovery-error, role-change, and last-owner-protection states with representative production content and users with disabilities.
