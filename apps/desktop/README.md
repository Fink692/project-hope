# Project Hope desktop installer

This package creates the normal desktop experience for a hosted Project Hope workspace. The installer puts a Project Hope app in the Start menu, Applications folder, or Linux launcher; it does not install Docker, databases, or developer tooling on a charity staff member’s computer.

The setup partner builds a preconfigured installer for the organization’s HTTPS workspace:

```powershell
$env:PROJECT_HOPE_APP_URL = "https://hope.example.org"
pnpm install --frozen-lockfile
pnpm run dist:win
```

The installer launches the workspace and remembers it. A generic installer with no address configured shows a friendly one-time connection screen instead of exposing infrastructure settings. Future signed releases can update through the built-in updater.

Build targets:

- Windows: NSIS installer (`.exe`)
- macOS: disk image and archive (`.dmg`, `.zip`)
- Linux: AppImage and Debian package (`.AppImage`, `.deb`)

The production installer should be built with the charity’s HTTPS address, organization-owned signing certificates, and a synthetic-data staging test before it is handed to staff.
