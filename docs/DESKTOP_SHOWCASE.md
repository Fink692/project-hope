# The included desktop sample

Version 1.9 includes the actual workspace engine and web application. Download from [Project Hope](https://project-hope-charities.vercel.app/#download). The [plain-language guide](https://project-hope-charities.vercel.app/guide) covers installation, optional AI, and connecting a hosted charity.

## What happens on first launch

Electron starts a bundled native Python application. It migrates a private SQLite sample database, seeds fictional records once, and signs into the local demonstration account. No development runtime or database installer is needed.

The account has no usable password. The local listener accepts only the exact loopback host and a random per-launch token added by the desktop main process. The token is not exposed to page JavaScript or passed on the command line. External sending, invitations, administrative login, and other sensitive actions are blocked in sample mode.

Sample edits are saved in the app profile. Closing the parent app stops the local engine. The app never points a sample at a production database supplied through inherited environment variables.

## Optional AI

The sample starts its own AI gateway. If compatible local Ollama models are available, it uses `qwen3:4b` and `all-minilm`. Model weights and Ollama are not included in the installer.

Without a model service, bounded deterministic adapters remain available. The UI identifies these results as safety templates, not generative AI; a fallback translation is not represented as completed translation. All outputs require review.

## Build and verify

Install the desktop and web dependencies, plus `services/core/requirements-desktop.txt` in a Python 3.12 environment. Then:

```text
pnpm --dir apps/desktop test
pnpm --dir apps/desktop build:bundle
pnpm --dir apps/desktop test:runtime
pnpm --dir apps/desktop exec electron-builder --win --publish never
```

Build the native runtime separately on each target operating system. The packaging hook refuses to build an installer without the engine and compiled web interface. The desktop workflow builds Windows, Apple-silicon macOS, and Linux artifacts.

The runtime integration check exercises new-profile startup, automatic sign-in, static assets, 15 module APIs, contact edits/export/duplicates, an AI workflow, blocked external actions, and persistence after restart. Website-side `tests/desktop-ui.mjs` can test a packaged executable with Playwright by passing its absolute path.

## Boundaries

This is a synthetic, single-computer preview. It is not a configured production database, a managed hosting service, an encrypted backup product, a signed installer, a live telephone service, or a mobile-store release. Do not enter real beneficiary or donor records into the sample.
