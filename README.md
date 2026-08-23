# Project Hope

### One calm workspace for the people doing the work.

[![Quality gate](https://github.com/Fink692/project-hope/actions/workflows/ci.yml/badge.svg)](https://github.com/Fink692/project-hope/actions/workflows/ci.yml)
[![Latest release](https://img.shields.io/github/v/release/Fink692/project-hope?display_name=tag&color=1f7a5a)](https://github.com/Fink692/project-hope/releases/latest)
[![Data control](https://img.shields.io/badge/data-charity--controlled-235347)](docs/full-build-status.md)

Project Hope gives charities one connected place to coordinate people, programs, volunteers, documents, schedules, grants, communications, and impact work.

It works like a normal app: staff install it, sign in, and get to work. The desktop, iPhone, and Android clients all use the same hosted organization workspace, so nobody has to keep separate copies of the truth.

![Project Hope Founding 10 application and managed pilot offer](docs/assets/founding-10.png)

### Secure onboarding that feels like a normal app

| Private team invitation | Owner-managed team access |
|---|---|
| ![Project Hope secure team invitation](docs/assets/team-invitation-live-v1.6.png) | ![Project Hope Team and access workspace](docs/assets/team-access-live-v1.6.png) |

### Built-in account protection

![Project Hope guided two-step verification setup with the private demo QR and key redacted](docs/assets/account-security-live-v1.7.png)

![Project Hope protected workspace showing one-time recovery codes redacted in the release image](docs/assets/recovery-codes-live-v1.7.png)

## Founding 10 managed pilot

Project Hope's source is publicly visible, but this repository does not yet include an approved software license, so reuse rights must not be assumed. The intended self-hosted Community offering is zero-cost once the copyright owner approves its licensing terms. The Founding 10 programme is for charities that want someone else to handle the technical launch and ongoing maintenance.

- **Founding Partner pilot:** CAD $149/month after the workspace is live
- **Included:** managed launch, first-admin onboarding, updates, encrypted backups, and human support
- **Pilot terms:** no setup fee, no charge to apply, no card collected during application, and cancel anytime
- **Data terms:** fit, scope, hosting region, and responsibilities are confirmed in writing before launch

The built-in application requires explicit consent, verifies every email, prevents duplicate applicants, and records privacy-safe funnel evidence. See the [commercial readiness runbook](docs/commercial-readiness.md) and [pilot privacy notice](docs/privacy/pilot-applications.md).

## Start here

| You are here for… | Go to… |
|---|---|
| Installing the app | [Download the latest desktop installers](https://github.com/Fink692/project-hope/releases/latest) |
| Running the Founding 10 programme | [Commercial readiness and launch runbook](docs/commercial-readiness.md) |
| Announcing the release | [LinkedIn release post](docs/launch/linkedin-release-post.md) |
| Finding the first pilot partners | [Permission-first outreach kit](docs/launch/founding-10-outreach-kit.md) |
| Understanding the charity experience | [Project Hope as an app](docs/DISTRIBUTION_FOR_CHARITIES.md) |
| Deploying a workspace for a charity | [Production deployment guide](docs/operations/production-deployment.md) |
| Running a local training workspace | [Getting Started for Charities](docs/GETTING_STARTED_FOR_CHARITIES.md) |
| Reviewing what is built | [Full build status](docs/full-build-status.md) |

## The charity experience

1. A setup partner deploys one secure Project Hope workspace.
2. The partner sends staff the installer or app download link.
3. Staff install Project Hope, sign in, and start working.
4. Records, permissions, review history, and updates stay connected across devices.

Staff do not install Docker, configure databases, manage backups, learn developer commands, or maintain local copies of the system.

### Download the desktop app

The [latest release](https://github.com/Fink692/project-hope/releases/latest) includes:

- **Windows:** one-click NSIS installer (`.exe`)
- **macOS:** disk image and archive (`.dmg`, `.zip`)
- **Linux:** AppImage and Debian package (`.AppImage`, `.deb`)

A generic desktop installer asks for the organization’s Project Hope address once, checks the connection, remembers it, and opens the workspace from then on. A setup partner can also build a preconfigured installer so staff only install and open it.

ChromeOS and supported browsers can use the browser-installable version. iPhone and Android builds use the same sign-in and hosted workspace; publishing them to the App Store and Google Play requires the organization’s own developer accounts and signing credentials.

## What is inside

- **Coordinate:** contacts, households, relationships, consent, volunteers, programs, events, shifts, waitlists, and calendar export.
- **Understand:** documents, bounded extraction, search, analytics, grants, evidence workflows, resources, translation, and donor insights.
- **Communicate safely:** minimized mailbox imports, injection flags, draft approval, email delivery, voice consent, callbacks, and transfer controls.
- **Extend responsibly:** governed plugins, scoped public API clients, capability tokens, append-only audit events, and human review.

The platform remains useful with AI disabled. AI features use bounded, replaceable adapters and keep consequential outputs reviewable by people.

## Built for trust

- Organization-scoped access, roles, permissions, audit history, and legal holds
- Built-in authenticator-app two-step verification, single-use recovery codes, encrypted MFA secrets, and automatic revocation of older sessions and app tokens after security changes
- Secure team onboarding with expiring one-time invitations, in-app role management, resend/revoke controls, and delivery retries
- Privacy-safe account recovery with one-hour single-use links and token/session invalidation
- Charity-controlled data with replaceable self-hosted infrastructure
- Human approval before consequential actions
- Accessible keyboard-first interfaces with reduced-motion support
- Safe upload handling, data minimization, and fail-closed production configuration
- No paid AI API or cloud service is a required dependency
- The one-command local stack prepares a private Ollama chat model and semantic embedding model automatically; no AI account or API key is required.

## For setup partners

The setup partner owns the one-time technical launch:

- deploy the production Compose stack;
- connect the organization’s domain and HTTPS;
- configure the built-in MFA encryption key and shared security cache, plus email, secrets, backups, and monitoring;
- create the organization’s mobile build/signing configuration;
- run a synthetic-data staging test;
- build a preconfigured desktop installer.

On Windows, the preconfigured installer command is:

```powershell
.\scripts\build-desktop.ps1 -ServerUrl "https://hope.example.org"
```

Read the [desktop installer guide](apps/desktop/README.md) and [production deployment guide](docs/operations/production-deployment.md) before handing an installer to staff. Code-signing certificates and the real production workspace URL are intentionally organization-owned launch requirements.

## Local training workspace

The local stack is for training, demonstrations, and technical support. It is not the normal staff distribution path.

### Windows

Install [Docker Desktop](https://www.docker.com/products/docker-desktop/) or [Podman Desktop](https://podman-desktop.io/downloads), open it, then run:

```powershell
.\scripts\project-hope.ps1 setup
```

### macOS or Linux

```bash
bash scripts/project-hope.sh setup
```

The helper starts the local workspace, waits for health, opens the browser, and shows the demo sign-in. See [Getting Started for Charities](docs/GETTING_STARTED_FOR_CHARITIES.md) for the plain-language walkthrough.

## Developer workspace

The repository is organized as a modular monolith with replaceable clients:

| Area | Location |
|---|---|
| Domain API and workers | `services/core` |
| Web app and PWA shell | `apps/web` |
| Native mobile client | `apps/mobile` |
| Native desktop installers | `apps/desktop` |
| Compose and reverse proxy | `deploy/podman` |
| Architecture, operations, and decisions | `docs` |

### Web development

```powershell
cd apps/web
pnpm install
pnpm dev
```

The web shell runs at `http://127.0.0.1:5173/` and proxies `/api` to Django.

### API development

```powershell
cd services/core
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements-dev.txt
$env:DJANGO_SETTINGS_MODULE = "project.settings"
python manage.py migrate
python manage.py seed_demo
python manage.py runserver
```

### Verification

```powershell
cd services/core
python manage.py check
python manage.py test
ruff check project audit identity
mypy .

cd ..\..\apps\web
pnpm test
pnpm build

cd ..\desktop
pnpm install --frozen-lockfile
pnpm run build
```

GitHub Actions also verifies the backend, web client, mobile client, desktop packaging matrix, onboarding helpers, Compose files, and production configuration.

## Release status

The current public release is [Project Hope 1.7.0](https://github.com/Fink692/project-hope/releases/tag/v1.7.0), with built-in two-step verification and recovery, secure team onboarding, native desktop installers, the local AI runtime, and the Founding 10 acquisition workflow. The [full build status](docs/full-build-status.md) records the implemented product surface and the remaining organization-owned launch requirements.

## Principles

- Charity-controlled data and replaceable infrastructure
- Human authority over model authority
- Explicit tenant and program scope
- Least privilege and append-only audit history
- Accessible interfaces and keyboard-first workflows
- Useful operations even when AI is disabled
