# Getting Project Hope running

This guide is written for charity teams, coordinators, and volunteers who should not need to understand servers or software engineering to get started.

## The easiest local setup

This starts Project Hope on one computer. It is ideal for trying the platform, training a small team, or preparing a staging workspace.

### 1. Install one container app

Choose one:

- [Docker Desktop](https://www.docker.com/products/docker-desktop/)
- [Podman Desktop](https://podman-desktop.io/downloads)

Open the app and wait until it says it is running. You do not need to create an account or learn the command line.

### 2. Start Project Hope

Download or copy this repository, then open a terminal in its folder.

On Windows, double-click `scripts\project-hope.cmd`, or run:

```powershell
.\scripts\project-hope.ps1 setup
```

If Windows blocks the script, use this one-time command in PowerShell:

```powershell
Set-ExecutionPolicy -Scope Process Bypass
.\scripts\project-hope.ps1 setup
```

On macOS or Linux, run:

```bash
bash scripts/project-hope.sh setup
```

The helper starts the services, waits for the health check, and opens the workspace at [http://localhost:8090](http://localhost:8090).

The first setup also prepares the local AI runtime automatically. It downloads the configured chat and embedding models into the private Project Hope model volume. This can take several minutes and needs several gigabytes of free disk space, but it does not require an AI account, API key, or cloud subscription. The workspace remains usable while the models are being prepared; the status card will say when AI is ready.

### 3. Sign in

The local training workspace opens with a safe demo organization:

| Field | Value |
|---|---|
| Email | `demo@example.org` |
| Password | `change-me-now` |

This account is only for local setup. Do not put real client information into the demo environment until an administrator has completed the production identity and privacy setup.

## The five commands a coordinator needs

You do not need to remember Docker or Podman commands:

```text
setup    Start the workspace for the first time
start    Start it again tomorrow
stop     Stop it without deleting its data
status   See whether everything is ready
logs     Show recent service messages if a helper asks for them
```

Use the same `scripts\project-hope.ps1` command on Windows or `scripts/project-hope.sh` on macOS/Linux, followed by the command name.

## What each person needs to know

- **Coordinator:** run `setup`, open the browser, and share the local address with the team on the same computer/network only after access is configured.
- **Staff member:** sign in, choose the organization, and start with CRM, Volunteers, or Scheduling. Every record stays inside the organization boundary.

### Invite your team

An owner or administrator opens **Team & access**, enters a teammate's work email, chooses a role, and selects **Send invitation**. The teammate receives a private link that expires after seven days by default. A new teammate chooses a password in the link; someone who already has a Project Hope account accepts and signs in normally. Owners and administrators can resend or revoke pending links and change active member roles from the same screen.

If mail delivery is temporarily unavailable, Project Hope shows that delivery is retrying and the background worker tries again. Never copy invitation links into public chats or documents.

If someone forgets a password, select **Forgot password?** on the sign-in screen. Project Hope gives the same immediate privacy-safe response for every address and, when an active account matches, the background worker emails a one-hour single-use reset link. Changing the password signs out existing sessions and revokes the account's API token.

### Protect your account

Real deployments require two-step verification before organization information opens. On first sign-in, **Account security** guides you to scan a private QR code with any standards-based authenticator app, confirm the current six-digit code, and save a one-time recovery-code set. The QR key and recovery codes should be treated like passwords; put the recovery set in a password manager or another private place, never a shared chat or public document.

Future sign-ins ask for the current authenticator code after the password. If the authenticator is unavailable, choose **Use a recovery code**. Each recovery code works once. After using one, open **Account security** in the browser and create a replacement set. If both the authenticator and recovery set are unavailable, contact the designated Project Hope operator; support must verify identity under the charity's recovery procedure before resetting the factor.

Native mobile/API sign-ins expire after 30 days by default. If the app asks someone to sign in again, this is expected token rotation; no organization data is deleted.
- **Administrator:** use the production deployment guide before real data, public access, or staff-wide rollout.
- **Support helper:** ask the coordinator to run `status` first. If needed, `logs` shows recent service information without changing data.

## What “AI ready” means

Project Hope uses a local Ollama runtime for bounded classification, drafting, translation, plain-language rewrites, evidence-grounded grant answers, and semantic embeddings. Every generated result remains reviewable, and sending, publishing, eligibility decisions, permissions, and crisis responses stay with a human.

If the model computer is unavailable or too small, Project Hope falls back to its deterministic safety adapter. That fallback is safe and testable, but it is not a general-purpose language model. The status command and gateway health endpoint make this distinction visible.

## If something goes wrong

1. Make sure Docker Desktop or Podman Desktop is open and says it is running.
2. Run `doctor` to check the computer.
3. Run `status` and wait one minute on the first launch.
4. If the browser says the site cannot be reached, restart with `start`.
5. Share the output of `status` and the last part of `logs` with your support person. Never share passwords, secret files, or exported client data.

## Moving beyond a local trial

The local setup is intentionally simple and uses demo credentials. A real charity deployment needs a domain, HTTPS, organization-owned secrets, MFA-backed identity, email delivery, encrypted backups, a restore drill, and a staging test with synthetic data. Follow [production deployment](operations/production-deployment.md) and the [release checklist](release-checklist.md) before importing real records.

Project Hope is designed so a charity can get help without handing over control: the platform remains self-hosted, AI is optional, consequential actions stay reviewable, and the setup path is documented in plain language.
