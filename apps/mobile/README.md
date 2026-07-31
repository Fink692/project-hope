# Project Hope mobile client

This Expo/React Native client shares the tenant-bound REST API contract with the web app. It is a bounded field workspace: schedules, volunteer work, contact tasks, resources, approved documents, and expiring safe cached snapshots are available; broad CRM exports and local model execution are not.

Authentication uses the API token returned by the shared login endpoint and Expo secure device storage. Sign-out revokes the server token and clears the device credential.

```powershell
cd apps/mobile
pnpm install
$env:EXPO_PUBLIC_API_URL = "http://127.0.0.1:8000/api/v1"
pnpm start
```

Native distribution, device-management policy, encrypted storage validation, and remote sign-out testing are required before publishing to an app store.

Release profiles are in eas.json. Configure an organization-owned EAS project, signing credentials, privacy disclosures, and a real-device staging test before running the production profile. Set `EXPO_PUBLIC_API_URL` to the complete HTTPS API base (for example, `https://hope.example.org/api/v1`); release mode refuses to use a localhost fallback.

For EAS, create the variable in the matching EAS environment before building:

```powershell
eas env:create --name EXPO_PUBLIC_API_URL --value https://hope.example.org/api/v1 --environment production
```
