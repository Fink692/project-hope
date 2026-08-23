# Project Hope 1.7 accessibility evidence

- Date: 2026-08-23
- Scope: browser two-step sign-in and required authenticator enrollment, including recovery-code disclosure and account-security management
- Target: WCAG 2.2 Level AA engineering baseline

This is engineering evidence, not a legal certification or a substitute for testing with people who use assistive technology.

## Automated result

The Vitest suite runs axe-core 4.13.0 with the `wcag2a`, `wcag2aa`, `wcag21a`, `wcag21aa`, and `wcag22aa` rule tags. The two-step challenge and required-enrollment journeys report zero automated violations. They are part of a 13-test web interaction suite.

The tests verify named regions and controls, semantic headings, visible labels, alert/status output, authenticator-versus-recovery mode selection, a QR image with alternative text, manual-key fallback, one-time recovery-code presentation, keyboard-operable copy/download actions, enrollment-required workspace blocking, and private challenges remaining out of the URL and browser storage. Color contrast remains excluded from jsdom because it cannot calculate painted backgrounds reliably; the unchanged shared palette has the browser-assisted contrast evidence recorded in `accessibility-audit-v1.5.md`.

## Interaction review

- The challenge view keeps one clear task and supports both six-digit and recovery-code input without relying on color.
- Enrollment explains why it is required, provides QR and selectable manual-key paths, marks the secret as private, and places recovery codes in a labelled one-time region.
- Busy, disabled, success, and error states have text or accessibility-state equivalents.
- Focus-visible and reduced-motion rules apply to the new controls; narrow layouts stack setup and recovery actions without horizontal scrolling.
- Organization navigation and records are not rendered while required enrollment is incomplete.

## Remaining external gate

Before claiming WCAG 2.2 AA conformance for a deployed service, complete keyboard-only and 200%/400% zoom checks plus current NVDA/Firefox or Chrome, VoiceOver/Safari, and supported mobile screen-reader journeys. Include wrong/expired/replayed codes, QR zoom, manual setup, recovery-code download, low-code warning, operator-reset return, and authenticator-loss scenarios with representative users, including people with cognitive, vision, and motor disabilities.
