# Project Hope as an app

Project Hope is designed to feel like one normal app, even though it has a web client, mobile clients, and a secure shared server underneath.

## What a charity receives

1. A single secure Project Hope web address, such as `https://hope.example.org`.
2. A desktop installation from the browser—Windows, macOS, or ChromeOS.
3. An iPhone and Android app built from the same Project Hope workspace.
4. One sign-in, one organization boundary, and the same records on every device.

Staff do not install Docker, configure databases, manage backups, or learn developer commands.

## What the charity sees

### Desktop

Open the Project Hope address in Chrome or Edge. Choose the install icon in the address bar or browser menu, then choose **Install Project Hope**. It will appear like a normal desktop application and open in its own window.

On Safari, choose **File → Add to Dock** on supported macOS versions.

### iPhone and Android

The organization’s setup partner publishes the Expo client through its Apple App Store and Google Play accounts. The app is configured with the charity’s secure Project Hope address before release, so staff only download it, sign in, and work.

## What happens behind the scenes

The charity has one hosted Project Hope server. The web app and mobile app use the same tenant-scoped API, authentication boundary, audit trail, backups, and review controls. Updates are made once on the hosted service instead of being installed on every staff computer.

```text
Staff devices
  ├── Desktop install (web app)
  ├── iPhone app
  └── Android app
          │
          ▼
   One hosted Project Hope workspace
          │
          ├── Organization data and permissions
          ├── Backups and audit history
          └── Optional local AI gateway
```

## The only setup work

A technical setup partner or hosting provider completes this once:

- deploys the production Compose stack;
- connects the organization’s domain and HTTPS certificate;
- configures MFA-backed identity, email, secrets, backups, and monitoring;
- creates the EAS project and signs the iPhone/Android builds;
- completes a synthetic-data staging test.

After that, the charity’s coordinator sends staff the address and app download links. The charity never needs to understand the infrastructure underneath.

## Why this is the right model

Because offline use is not required, a shared hosted workspace is safer and easier to support than shipping a database inside every download. There is one source of truth, one backup plan, one update path, and no drift between devices.

See the [production deployment guide](operations/production-deployment.md) for the setup partner and the [Getting Started for Charities guide](GETTING_STARTED_FOR_CHARITIES.md) for local training environments.
