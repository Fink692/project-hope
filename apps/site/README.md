# Project Hope showcase

The public product site runs on Vercel at https://project-hope-charities.vercel.app. It is a standard Next.js application, not a Sites project.

## Local development

```text
pnpm install --frozen-lockfile
pnpm dev --port 5180
pnpm test
pnpm lint
pnpm build
pnpm test:e2e
```

Browser checks use Playwright and an installed Chrome on Windows. On a Linux CI runner, install Chromium with `pnpm exec playwright install --with-deps chromium` first. Set `HOPE_SITE_URL` to test the production site instead of localhost.

## Download delivery

Installer filenames, sizes, SHA-256 checksums, and availability are recorded in `lib/release-manifest.json`. Only verified artifacts have enabled download buttons. Binary installers are stored in a public Vercel Blob store and served through same-origin `/downloads/...` rewrites. Visitors do not navigate to a release repository or another website to download.

Do not put Blob write tokens in client code. Keep `.env.local` and `.vercel` ignored. Do not overwrite a published version with different bytes: publish a new version and update its manifest and routes.

The current Vercel Hobby plan has usage limits. Downloads can become unavailable if the provider quota is exhausted; this is not unlimited managed hosting.

## Deployment

Link to the existing Project Hope Vercel project, then deploy using Vercel CLI. Validate a preview before assigning the public alias. Preserve the public download routes and the published checksums during updates.

The public site contains no signup form, analytics script, repository link, or fake download-progress meter. Motion respects system preferences, can be paused, and does not hide content if JavaScript is disabled.

## Brand assets

See `docs/BRAND.md` for the built-in imagegen prompt and saved logo paths.
