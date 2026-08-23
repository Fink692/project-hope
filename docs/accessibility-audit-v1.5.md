# Project Hope 1.5 accessibility audit

- Date: 2026-08-23
- Scope: public web journey, Founding 10 application, sign-in/onboarding content, installer cards, and first-run responsive layout
- Target: WCAG 2.2 Level AA engineering baseline

This is release evidence, not a legal certification or a substitute for testing with people who use assistive technology.

## Automated result

The production web build was scanned in headless Chrome 151 with axe-core 4.13.0 using the `wcag2a`, `wcag2aa`, `wcag21a`, `wcag21aa`, and `wcag22aa` rule tags.

- Initial result: one serious color-contrast rule covering 41 nodes.
- Remediation: darkened the shared muted-text token, card copy, roadmap badges, and numbered onboarding accents.
- Retest: zero violations, 30 passed rules, and one incomplete contrast rule caused by the intentionally layered Founding 10 background.
- Manual contrast review of that layered section found a minimum relevant text/background ratio of 4.58:1; ordinary small text meets or exceeds 4.5:1.

The Vitest suite also runs axe-core against the rendered public journey on every CI build. Browser-based color contrast remains a release check because jsdom cannot calculate painted backgrounds reliably.

## Manual and browser-assisted checks

- The first keyboard stop is the visible “Skip to main content” link.
- Native links, buttons, radio buttons, checkboxes, inputs, selects, and textareas follow DOM order and retain visible focus indicators.
- The public page has one level-one heading and no skipped heading levels.
- All tabbable form controls have a programmatic label; dynamic success and error messages use status or alert live regions.
- The confirmation token is removed before rendering status and new links keep it in the URL fragment so it is not sent in HTTP requests or referrers.
- At a true 320 CSS-pixel viewport, document and body widths remain 320 pixels with no horizontal overflow; the pilot and form collapse to one column.
- Reduced-motion preferences disable smooth scrolling and hover movement.
- Information is not communicated by color alone; status labels and text accompany visual treatment.

## Remaining launch validation

Before a production operator advertises the service, test the deployed domain at 200% browser zoom and with current versions of NVDA plus Firefox/Chrome, VoiceOver plus Safari, and the operator's supported mobile screen reader. Repeat the form, validation-error, email-confirmation, sign-in, and workspace journeys with real production content and keyboard-only input.
