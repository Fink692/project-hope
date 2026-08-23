import { useCallback, useEffect, useMemo, useState } from "react";
import {
  ActivityIndicator,
  Alert,
  FlatList,
  KeyboardAvoidingView,
  Linking,
  Platform,
  Pressable,
  RefreshControl,
  SafeAreaView,
  ScrollView,
  StyleSheet,
  Text,
  TextInput,
  View,
} from "react-native";
import { StatusBar } from "expo-status-bar";
import * as SecureStore from "expo-secure-store";

type Module = {
  id: string;
  endpoint: string;
  label: string;
  description: string;
  accent: string;
};

type Organization = { id: string; name: string; slug: string; status: string };
type Session = {
  user: { email: string; display_name: string };
  organizations: Array<{ organization: Organization; role: string }>;
  mfa?: MfaStatus;
  workspaceAccessGranted?: boolean;
};
type MfaStatus = { enabled: boolean; required: boolean; enrollmentRequired: boolean; enabledAt: string | null; recoveryCodesRemaining: number };
type MfaChallenge = { challenge: string; expiresInSeconds: number; methods: string[] };
type MfaEnrollment = { enrollmentToken: string; formattedSecret: string; otpauthUri: string; expiresInSeconds: number };

const modules: Module[] = [
  { id: "contacts", endpoint: "contacts", label: "People", description: "Contacts, consent, and follow-up", accent: "#d5e2d6" },
  { id: "volunteers", endpoint: "volunteer-applications", label: "Volunteers", description: "Applications and onboarding", accent: "#cfdbed" },
  { id: "schedules", endpoint: "schedules", label: "My schedule", description: "Appointments and shifts", accent: "#e2d9c5" },
  { id: "resources", endpoint: "resources", label: "Resources", description: "Verified community services", accent: "#f2d3bf" },
  { id: "documents", endpoint: "documents", label: "Documents", description: "Approved source material", accent: "#d5e2d6" },
  { id: "calls", endpoint: "calls", label: "Phone workspace", description: "Consent and human escalation", accent: "#cfdbed" },
];

const AUTH_KEY = "project-hope-mobile-token";
const LEGACY_NOTE_KEY = "project-hope-mobile-note";
type ConnectionState = "checking" | "online" | "unavailable";

function normalizeBaseUrl(value: string) {
  return value.replace(/\/+$/, "");
}

async function purgeLegacyOfflineData(session: Session) {
  const recordKeys = session.organizations.flatMap(({ organization }) =>
    modules.map(
      (module) =>
        "project-hope-cache-" + organization.slug + "-" + module.endpoint,
    ),
  );
  await Promise.allSettled(
    [LEGACY_NOTE_KEY, ...recordKeys].map((key) => SecureStore.deleteItemAsync(key)),
  );
}

async function apiRequest<T>(
  baseUrl: string,
  path: string,
  token?: string,
  init: RequestInit = {},
): Promise<T> {
  const headers = new Headers(init.headers);
  headers.set("Accept", "application/json");
  if (init.body && !headers.has("Content-Type")) headers.set("Content-Type", "application/json");
  if (token) headers.set("Authorization", "Token " + token);
  const response = await fetch(baseUrl + path, { ...init, headers });
  const body = await response.json().catch(() => ({}));
  if (!response.ok) {
    const error = new Error(body.detail ?? "Request failed (" + response.status + ")");
    (error as Error & { status?: number }).status = response.status;
    throw error;
  }
  return body as T;
}

function LoginScreen({ baseUrl, onAuthenticated }: { baseUrl: string; onAuthenticated: (token: string) => Promise<void> }) {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [challenge, setChallenge] = useState<MfaChallenge | null>(null);
  const [verificationCode, setVerificationCode] = useState("");
  const [useRecoveryCode, setUseRecoveryCode] = useState(false);

  async function submit() {
    if (!email.trim() || !password) {
      setError("Enter your email and password.");
      return;
    }
    setBusy(true);
    setError("");
    try {
      const result = await apiRequest<{ token?: string; mfaRequired?: boolean; challenge?: string; expiresInSeconds?: number; methods?: string[] }>(baseUrl, "/auth/token/", undefined, {
        method: "POST",
        body: JSON.stringify({ email: email.trim(), password }),
      });
      if (result.mfaRequired && result.challenge) {
        setChallenge({ challenge: result.challenge, expiresInSeconds: result.expiresInSeconds ?? 300, methods: result.methods ?? ["totp", "recovery_code"] });
        setPassword("");
        return;
      }
      if (!result.token) throw new Error("The server did not issue a device credential.");
      await SecureStore.setItemAsync(AUTH_KEY, result.token);
      await onAuthenticated(result.token);
      setPassword("");
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Unable to sign in.");
    } finally {
      setBusy(false);
    }
  }

  async function verifyChallenge() {
    if (!challenge || !verificationCode.trim()) {
      setError("Enter your authenticator or recovery code.");
      return;
    }
    setBusy(true);
    setError("");
    try {
      const result = await apiRequest<{ token: string; recoveryCodeUsed?: boolean }>(baseUrl, "/auth/mfa/challenge/", undefined, {
        method: "POST",
        body: JSON.stringify({ challenge: challenge.challenge, code: verificationCode.trim() }),
      });
      await SecureStore.setItemAsync(AUTH_KEY, result.token);
      await onAuthenticated(result.token);
      setChallenge(null);
      setVerificationCode("");
      if (result.recoveryCodeUsed) Alert.alert("Recovery code used", "That code cannot be used again. Create a replacement set from Account security when you can.");
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Unable to verify this sign-in.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <KeyboardAvoidingView behavior={Platform.OS === "ios" ? "padding" : undefined} style={styles.safe}>
      <ScrollView contentContainerStyle={styles.loginContainer} keyboardShouldPersistTaps="handled">
        <Text style={styles.eyebrow}>PROJECT HOPE · FIELD WORKSPACE</Text>
        <Text style={styles.title}>{challenge ? "Confirm it’s you." : "Good work starts with a clear next step."}</Text>
        <Text style={styles.body}>{challenge ? "Use the current code from your authenticator app. The private sign-in challenge expires in about " + Math.max(1, Math.round(challenge.expiresInSeconds / 60)) + " minutes." : "Sign in to access the minimum organization-scoped information needed in the field."}</Text>
        <View style={styles.formCard}>
          {challenge ? <>
          <Text style={styles.label}>{useRecoveryCode ? "Recovery code" : "Authenticator code"}</Text>
          <TextInput
            accessibilityLabel={useRecoveryCode ? "Recovery code" : "Authenticator code"}
            autoCapitalize={useRecoveryCode ? "characters" : "none"}
            autoComplete="sms-otp"
            keyboardType={useRecoveryCode ? "default" : "number-pad"}
            maxLength={useRecoveryCode ? 16 : 6}
            onChangeText={setVerificationCode}
            onSubmitEditing={verifyChallenge}
            placeholder={useRecoveryCode ? "XXXXX-XXXXX" : "000000"}
            placeholderTextColor="#87928b"
            style={styles.input}
            textContentType="oneTimeCode"
            value={verificationCode}
          />
          {error ? <Text accessibilityRole="alert" style={styles.error}>{error}</Text> : null}
          <Pressable accessibilityLabel={busy ? "Verifying" : "Verify and sign in"} accessibilityRole="button" accessibilityState={{ busy, disabled: busy }} disabled={busy} onPress={verifyChallenge} style={styles.primaryButton}>
            {busy ? <ActivityIndicator color="#fff" /> : <Text style={styles.primaryButtonText}>Verify and sign in</Text>}
          </Pressable>
          <Pressable accessibilityRole="button" disabled={busy} onPress={() => { setUseRecoveryCode(!useRecoveryCode); setVerificationCode(""); setError(""); }} style={styles.secondaryButton}><Text style={styles.secondaryButtonText}>{useRecoveryCode ? "Use authenticator code" : "Use a recovery code"}</Text></Pressable>
          <Pressable accessibilityRole="button" disabled={busy} onPress={() => { setChallenge(null); setVerificationCode(""); setError(""); }} style={styles.linkButton}><Text style={styles.linkButtonText}>Back to password sign-in</Text></Pressable>
          </> : <>
          <Text style={styles.label}>Work email</Text>
          <TextInput
            accessibilityLabel="Work email"
            autoCapitalize="none"
            autoComplete="email"
            keyboardType="email-address"
            onChangeText={setEmail}
            placeholder="you@charity.org"
            placeholderTextColor="#87928b"
            style={styles.input}
            value={email}
          />
          <Text style={styles.label}>Password</Text>
          <TextInput
            accessibilityLabel="Password"
            autoCapitalize="none"
            autoComplete="current-password"
            onChangeText={setPassword}
            onSubmitEditing={submit}
            placeholder="Your password"
            placeholderTextColor="#87928b"
            secureTextEntry
            style={styles.input}
            value={password}
          />
          {error ? <Text accessibilityRole="alert" style={styles.error}>{error}</Text> : null}
          <Pressable accessibilityLabel={busy ? "Signing in" : "Sign in securely"} accessibilityRole="button" accessibilityState={{ busy, disabled: busy }} disabled={busy} onPress={submit} style={styles.primaryButton}>
            {busy ? <ActivityIndicator color="#fff" /> : <Text style={styles.primaryButtonText}>Sign in securely</Text>}
          </Pressable>
          </>}
        </View>
        <Text style={styles.caption}>Your access token is stored in secure device storage. Sign out to revoke it.</Text>
      </ScrollView>
    </KeyboardAvoidingView>
  );
}

function MfaEnrollmentScreen({ baseUrl, token, onCompleted, onSignOut }: { baseUrl: string; token: string; onCompleted: () => Promise<void>; onSignOut: () => Promise<void> }) {
  const [currentPassword, setCurrentPassword] = useState("");
  const [code, setCode] = useState("");
  const [enrollment, setEnrollment] = useState<MfaEnrollment | null>(null);
  const [recoveryCodes, setRecoveryCodes] = useState<string[]>([]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  async function begin() {
    if (!currentPassword) {
      setError("Enter your current password.");
      return;
    }
    setBusy(true);
    setError("");
    try {
      const result = await apiRequest<MfaEnrollment>(baseUrl, "/auth/mfa/enrollment/", token, {
        method: "POST",
        body: JSON.stringify({ current_password: currentPassword }),
      });
      setEnrollment(result);
      setCode("");
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Unable to start account protection.");
    } finally {
      setBusy(false);
    }
  }

  async function openAuthenticator() {
    if (!enrollment) return;
    try {
      await Linking.openURL(enrollment.otpauthUri);
    } catch {
      setError("No authenticator app accepted the setup link. Enter the displayed key manually in your authenticator app.");
    }
  }

  async function confirm() {
    if (!enrollment || !/^\d{6}$/.test(code)) {
      setError("Enter the current six-digit code from your authenticator app.");
      return;
    }
    setBusy(true);
    setError("");
    try {
      const result = await apiRequest<{ recoveryCodes: string[] }>(baseUrl, "/auth/mfa/enrollment/confirm/", token, {
        method: "POST",
        body: JSON.stringify({ enrollment_token: enrollment.enrollmentToken, code }),
      });
      setEnrollment(null);
      setCurrentPassword("");
      setCode("");
      setRecoveryCodes(result.recoveryCodes);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Unable to verify this authenticator.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <SafeAreaView style={styles.safe}>
      <KeyboardAvoidingView behavior={Platform.OS === "ios" ? "padding" : undefined} style={styles.safe}>
        <ScrollView contentContainerStyle={styles.loginContainer} keyboardShouldPersistTaps="handled">
          <Text style={styles.eyebrow}>ACCOUNT PROTECTION</Text>
          <Text style={styles.title}>{recoveryCodes.length ? "Save your recovery codes." : "Protect your workspace."}</Text>
          {recoveryCodes.length ? <>
            <Text style={styles.body}>Each code works once if your authenticator is unavailable. Store them in a password manager or another private place. Project Hope cannot show them again.</Text>
            <View accessibilityLabel="One-time recovery codes" style={styles.recoveryCard}>
              {recoveryCodes.map((recoveryCode) => <Text key={recoveryCode} selectable style={styles.recoveryCode}>{recoveryCode}</Text>)}
            </View>
            <Pressable accessibilityRole="button" onPress={() => void onCompleted()} style={styles.primaryButton}><Text style={styles.primaryButtonText}>I saved them · sign in again</Text></Pressable>
          </> : enrollment ? <>
            <Text style={styles.body}>Open the setup link in your authenticator app. If it does not open, add an account manually with the private key below.</Text>
            <View style={styles.formCard}>
              <Pressable accessibilityRole="button" onPress={() => void openAuthenticator()} style={styles.primaryButton}><Text style={styles.primaryButtonText}>Open authenticator app</Text></Pressable>
              <Text style={styles.label}>Manual setup key</Text>
              <Text accessibilityLabel="Manual authenticator setup key" selectable style={styles.manualKey}>{enrollment.formattedSecret}</Text>
              <Text style={styles.caption}>Treat this key like a password. Setup expires in about {Math.max(1, Math.round(enrollment.expiresInSeconds / 60))} minutes.</Text>
              <Text style={styles.label}>Six-digit authenticator code</Text>
              <TextInput accessibilityLabel="Six-digit authenticator code" autoComplete="sms-otp" keyboardType="number-pad" maxLength={6} onChangeText={setCode} onSubmitEditing={confirm} placeholder="000000" placeholderTextColor="#87928b" style={styles.input} textContentType="oneTimeCode" value={code} />
              {error ? <Text accessibilityRole="alert" style={styles.error}>{error}</Text> : null}
              <Pressable accessibilityRole="button" accessibilityState={{ busy, disabled: busy }} disabled={busy} onPress={confirm} style={styles.primaryButton}>{busy ? <ActivityIndicator color="#fff" /> : <Text style={styles.primaryButtonText}>Verify and turn on</Text>}</Pressable>
              <Pressable accessibilityRole="button" disabled={busy} onPress={() => { setEnrollment(null); setCode(""); setError(""); }} style={styles.secondaryButton}><Text style={styles.secondaryButtonText}>Start over</Text></Pressable>
            </View>
          </> : <>
            <Text style={styles.body}>Your organization requires two-step verification before its data can open. You can use any standards-based authenticator app.</Text>
            <View style={styles.formCard}>
              <Text style={styles.label}>Current password</Text>
              <TextInput accessibilityLabel="Current password" autoCapitalize="none" autoComplete="current-password" onChangeText={setCurrentPassword} onSubmitEditing={begin} placeholder="Your password" placeholderTextColor="#87928b" secureTextEntry style={styles.input} value={currentPassword} />
              {error ? <Text accessibilityRole="alert" style={styles.error}>{error}</Text> : null}
              <Pressable accessibilityRole="button" accessibilityState={{ busy, disabled: busy }} disabled={busy} onPress={begin} style={styles.primaryButton}>{busy ? <ActivityIndicator color="#fff" /> : <Text style={styles.primaryButtonText}>Set up two-step verification</Text>}</Pressable>
              <Pressable accessibilityRole="button" disabled={busy} onPress={() => void onSignOut()} style={styles.linkButton}><Text style={styles.linkButtonText}>Sign out</Text></Pressable>
            </View>
          </>}
        </ScrollView>
      </KeyboardAvoidingView>
    </SafeAreaView>
  );
}

function StatusPill({ online }: { online: ConnectionState }) {
  const label = online === "checking" ? "Checking connection…" : online === "online" ? "Connected" : "Connection unavailable";
  return (
    <View accessibilityLiveRegion="polite" accessible accessibilityRole="text" style={styles.statusPill}>
      <View style={[styles.statusDot, online === "online" ? styles.good : styles.warn]} />
      <Text style={styles.statusText}>{label}</Text>
    </View>
  );
}

function ConfigurationRequired() {
  return (
    <SafeAreaView style={styles.safe}>
      <View style={styles.loading}>
        <Text style={styles.eyebrow}>PROJECT HOPE</Text>
        <Text style={styles.moduleTitle}>This release needs its server address.</Text>
        <Text style={styles.body}>Set EXPO_PUBLIC_API_URL to the organization’s HTTPS API URL before building a preview or production app.</Text>
      </View>
    </SafeAreaView>
  );
}

function Workspace({
  baseUrl,
  token,
  session,
  online,
  onSignOut,
}: {
  baseUrl: string;
  token: string;
  session: Session;
  online: ConnectionState;
  onSignOut: () => Promise<void>;
}) {
  const [organizationSlug, setOrganizationSlug] = useState(session.organizations[0]?.organization.slug ?? "");
  const [selected, setSelected] = useState<Module | null>(null);
  const organization = useMemo(
    () => session.organizations.find(({ organization: item }) => item.slug === organizationSlug)?.organization ?? session.organizations[0]?.organization,
    [organizationSlug, session.organizations],
  );
  if (!organization) return <Text style={styles.error}>No active organization is available.</Text>;

  return (
    <SafeAreaView style={styles.safe}>
      <View style={styles.appContainer}>
        <View style={styles.topBar}>
          <View>
            <Text style={styles.eyebrow}>PROJECT HOPE</Text>
            <Text style={styles.topTitle}>{organization.name}</Text>
          </View>
          <Pressable accessibilityLabel="Sign out" accessibilityRole="button" onPress={() => void onSignOut()} style={styles.avatar}>
            <Text style={styles.avatarText}>{session.user.display_name.charAt(0).toUpperCase()}</Text>
          </Pressable>
        </View>
        <StatusPill online={online} />
        {session.organizations.length > 1 ? (
          <ScrollView horizontal showsHorizontalScrollIndicator={false} contentContainerStyle={styles.orgList}>
            {session.organizations.map(({ organization: item }) => (
              <Pressable accessibilityRole="button" accessibilityState={{ selected: item.slug === organization.slug }} key={item.slug} onPress={() => { setOrganizationSlug(item.slug); setSelected(null); }} style={[styles.orgChip, item.slug === organization.slug && styles.orgChipSelected]}>
                <Text style={[styles.orgChipText, item.slug === organization.slug && styles.orgChipTextSelected]}>{item.name}</Text>
              </Pressable>
            ))}
          </ScrollView>
        ) : null}
        {selected ? (
          <ModuleScreen baseUrl={baseUrl} module={selected} organization={organization} token={token} onBack={() => setSelected(null)} />
        ) : (
          <FlatList
            accessibilityLabel="Workspace modules"
            contentContainerStyle={styles.list}
            data={modules}
            keyExtractor={(item) => item.id}
            ListHeaderComponent={<View><Text style={styles.welcome}>Hello, {session.user.display_name.split(" ")[0]}.</Text><Text style={styles.body}>Choose the work surface you need. Sensitive data stays on the charity server.</Text></View>}
            renderItem={({ item }) => (
              <Pressable accessibilityRole="button" onPress={() => setSelected(item)} style={[styles.moduleCard, { backgroundColor: item.accent }]}>
                <View style={styles.cardText}><Text style={styles.cardTitle}>{item.label}</Text><Text style={styles.body}>{item.description}</Text></View>
                <Text accessibilityElementsHidden style={styles.arrow}>›</Text>
              </Pressable>
            )}
          />
        )}
      </View>
    </SafeAreaView>
  );
}

function ModuleScreen({ baseUrl, module, organization, token, onBack }: { baseUrl: string; module: Module; organization: Organization; token: string; onBack: () => void }) {
  const [records, setRecords] = useState<unknown[]>([]);
  const [busy, setBusy] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState("");

  const load = useCallback(async (isRefresh = false) => {
    setError("");
    if (isRefresh) setRefreshing(true); else setBusy(true);
    try {
      const result = await apiRequest<unknown>(baseUrl, "/organizations/" + organization.slug + "/" + module.endpoint + "/", token);
      const next = Array.isArray(result) ? result : [];
      setRecords(next);
    } catch (reason) {
      const status = (reason as Error & { status?: number }).status;
      if (status === 401) {
        setError("Your session has expired. Sign out and sign in again.");
      } else {
        setError(reason instanceof Error ? reason.message : "Unable to load this workspace.");
      }
    } finally {
      setBusy(false);
      setRefreshing(false);
    }
  }, [baseUrl, module.endpoint, organization.slug, token]);

  useEffect(() => { void load(); }, [load]);

  return (
    <View style={styles.moduleScreen}>
      <Pressable accessibilityRole="button" onPress={onBack} style={styles.backButton}><Text style={styles.backText}>‹  All modules</Text></Pressable>
      <Text style={styles.eyebrow}>FIELD WORKSPACE</Text>
      <Text style={styles.moduleTitle}>{module.label}</Text>
      <Text style={styles.body}>{module.description}</Text>
      {error ? <View style={styles.errorCard}><Text accessibilityRole="alert" style={styles.error}>{error}</Text><Pressable accessibilityRole="button" onPress={() => void load(true)} style={styles.secondaryButton}><Text style={styles.secondaryButtonText}>Try again</Text></Pressable></View> : null}
      {busy ? <View style={styles.loading}><ActivityIndicator color="#1f5148" /><Text style={styles.caption}>Loading records…</Text></View> : records.length === 0 ? <View style={styles.emptyCard}><Text style={styles.cardTitle}>Nothing here yet</Text><Text style={styles.body}>New organization-controlled records will appear here when connected.</Text></View> : (
        <FlatList
          contentContainerStyle={styles.recordList}
          data={records}
          keyExtractor={(_, index) => String(index)}
          refreshControl={<RefreshControl onRefresh={() => void load(true)} refreshing={refreshing} tintColor="#1f5148" />}
          renderItem={({ item, index }) => <View style={styles.recordCard}><Text style={styles.cardTitle}>{recordTitle(item, index)}</Text><Text style={styles.caption}>{recordSummary(item)}</Text></View>}
        />
      )}
    </View>
  );
}

function recordTitle(item: unknown, index: number) {
  if (typeof item !== "object" || item === null) return "Record " + (index + 1);
  const record = item as Record<string, unknown>;
  return String(record.name ?? record.title ?? record.subject ?? record.applicant_name ?? record.key ?? "Record " + (index + 1));
}

function recordSummary(item: unknown) {
  if (typeof item !== "object" || item === null) return "";
  const record = item as Record<string, unknown>;
  return String(record.description ?? record.status ?? record.email ?? record.definition ?? "Organization-controlled record");
}

export default function App() {
  const [token, setToken] = useState<string | null>(null);
  const [session, setSession] = useState<Session | null>(null);
  const [online, setOnline] = useState<ConnectionState>("checking");
  const [booting, setBooting] = useState(true);
  const baseUrl = normalizeBaseUrl(
    process.env.EXPO_PUBLIC_API_URL ??
      (process.env.NODE_ENV === "production" ? "" : "http://127.0.0.1:8000/api/v1"),
  );

  const refreshHealth = useCallback(async () => {
    try {
      const health = await apiRequest<{ status: string }>(baseUrl, "/healthz/");
      setOnline(health.status === "ok" ? "online" : "unavailable");
    } catch {
      setOnline("unavailable");
    }
  }, [baseUrl]);

  const loadSession = useCallback(async (candidate: string) => {
    try {
      const next = await apiRequest<Session>(baseUrl, "/me/", candidate);
      await purgeLegacyOfflineData(next);
      setToken(candidate);
      setSession(next);
    } catch {
      await SecureStore.deleteItemAsync(AUTH_KEY);
      setToken(null);
      setSession(null);
    }
  }, [baseUrl]);

  useEffect(() => {
    if (!baseUrl) {
      setBooting(false);
      return;
    }
    void refreshHealth();
    SecureStore.getItemAsync(AUTH_KEY).then((stored) => {
      if (stored) return loadSession(stored);
      return undefined;
    }).finally(() => setBooting(false));
  }, [loadSession, refreshHealth]);

  async function signOut() {
    if (token) {
      try {
        await apiRequest(baseUrl, "/auth/logout/", token, { method: "POST", body: "{}" });
      } catch {
        // Local sign-out still clears the device credential if the server is unavailable.
      }
    }
    await SecureStore.deleteItemAsync(AUTH_KEY);
    setToken(null);
    setSession(null);
    Alert.alert("Signed out", "This device no longer has access to the workspace.");
  }

  async function finishMfaEnrollment() {
    await SecureStore.deleteItemAsync(AUTH_KEY);
    setToken(null);
    setSession(null);
    Alert.alert("Account protected", "Two-step verification is on. Sign in again with your new authenticator code.");
  }

  if (!baseUrl) {
    return <><StatusBar style="dark" /><ConfigurationRequired /></>;
  }
  if (booting) {
    return <SafeAreaView style={styles.safe}><StatusBar style="dark" /><View style={styles.loading}><ActivityIndicator color="#1f5148" /><Text style={styles.caption}>Preparing your workspace…</Text></View></SafeAreaView>;
  }
  if (!token || !session) {
    return <><StatusBar style="dark" /><LoginScreen baseUrl={baseUrl} onAuthenticated={loadSession} /></>;
  }
  if (session.mfa?.enrollmentRequired) {
    return <><StatusBar style="dark" /><MfaEnrollmentScreen baseUrl={baseUrl} onCompleted={finishMfaEnrollment} onSignOut={signOut} token={token} /></>;
  }
  return <><StatusBar style="dark" /><Workspace baseUrl={baseUrl} online={online} onSignOut={signOut} session={session} token={token} /></>;
}

const styles = StyleSheet.create({
  safe: { backgroundColor: "#f4f0e8", flex: 1 },
  loginContainer: { flexGrow: 1, justifyContent: "center", padding: 24 },
  appContainer: { flex: 1, paddingHorizontal: 20 },
  topBar: { alignItems: "center", flexDirection: "row", justifyContent: "space-between", paddingBottom: 14, paddingTop: 16 },
  eyebrow: { color: "#1f5148", fontSize: 11, fontWeight: "800", letterSpacing: 1.4, marginBottom: 10 },
  title: { color: "#1d2b2a", fontSize: 38, fontWeight: "700", letterSpacing: -1.2, lineHeight: 42, marginBottom: 14 },
  topTitle: { color: "#1d2b2a", fontSize: 22, fontWeight: "700" },
  welcome: { color: "#1d2b2a", fontSize: 30, fontWeight: "700", letterSpacing: -0.8, marginBottom: 8, marginTop: 24 },
  body: { color: "#6b7770", fontSize: 15, lineHeight: 22 },
  caption: { color: "#6b7770", fontSize: 13, lineHeight: 19 },
  formCard: { backgroundColor: "#fbfaf7", borderColor: "#d9d7cf", borderRadius: 18, borderWidth: 1, marginTop: 28, padding: 20 },
  label: { color: "#1d2b2a", fontSize: 13, fontWeight: "700", marginBottom: 7, marginTop: 12 },
  input: { backgroundColor: "#fff", borderColor: "#d9d7cf", borderRadius: 10, borderWidth: 1, color: "#1d2b2a", fontSize: 16, minHeight: 50, paddingHorizontal: 14 },
  error: { color: "#a83f31", fontSize: 14, fontWeight: "700", lineHeight: 20, marginTop: 12 },
  primaryButton: { alignItems: "center", backgroundColor: "#1f5148", borderRadius: 26, justifyContent: "center", marginTop: 20, minHeight: 52, paddingHorizontal: 18 },
  primaryButtonText: { color: "#fff", fontSize: 15, fontWeight: "800" },
  secondaryButton: { alignItems: "center", alignSelf: "flex-start", borderColor: "#1f5148", borderRadius: 22, borderWidth: 1, marginTop: 14, minHeight: 42, paddingHorizontal: 16, paddingVertical: 10 },
  secondaryButtonText: { color: "#1f5148", fontSize: 14, fontWeight: "800" },
  linkButton: { alignItems: "center", marginTop: 16, minHeight: 40, paddingVertical: 10 },
  linkButtonText: { color: "#1f5148", fontSize: 14, fontWeight: "800", textDecorationLine: "underline" },
  manualKey: { backgroundColor: "#e7efe9", borderRadius: 8, color: "#1f5148", fontFamily: Platform.select({ ios: "Menlo", android: "monospace", default: "monospace" }), fontSize: 15, letterSpacing: 1.2, lineHeight: 24, marginBottom: 10, padding: 12 },
  recoveryCard: { backgroundColor: "#fbfaf7", borderColor: "#6e9a88", borderRadius: 18, borderWidth: 2, gap: 8, marginTop: 22, padding: 18 },
  recoveryCode: { color: "#1f5148", fontFamily: Platform.select({ ios: "Menlo", android: "monospace", default: "monospace" }), fontSize: 17, fontWeight: "700", letterSpacing: 1.1, paddingVertical: 4, textAlign: "center" },
  statusPill: { alignItems: "center", alignSelf: "flex-start", backgroundColor: "#fbfaf7", borderColor: "#d9d7cf", borderRadius: 20, borderWidth: 1, flexDirection: "row", gap: 8, marginBottom: 4, paddingHorizontal: 12, paddingVertical: 9 },
  statusDot: { borderRadius: 6, height: 10, width: 10 },
  good: { backgroundColor: "#3c9b67" },
  warn: { backgroundColor: "#df765b" },
  statusText: { color: "#1d2b2a", fontSize: 13, fontWeight: "700" },
  avatar: { alignItems: "center", backgroundColor: "#1f5148", borderRadius: 22, height: 44, justifyContent: "center", width: 44 },
  avatarText: { color: "#fff", fontSize: 18, fontWeight: "800" },
  orgList: { gap: 8, paddingVertical: 12 },
  orgChip: { backgroundColor: "#e7e3da", borderRadius: 20, paddingHorizontal: 14, paddingVertical: 9 },
  orgChipSelected: { backgroundColor: "#1f5148" },
  orgChipText: { color: "#526259", fontSize: 13, fontWeight: "700" },
  orgChipTextSelected: { color: "#fff" },
  list: { gap: 12, paddingBottom: 30, paddingTop: 14 },
  moduleCard: { alignItems: "center", borderRadius: 16, flexDirection: "row", justifyContent: "space-between", minHeight: 92, padding: 18 },
  cardText: { flex: 1, paddingRight: 14 },
  cardTitle: { color: "#1d2b2a", fontSize: 17, fontWeight: "800", marginBottom: 5 },
  arrow: { color: "#1f5148", fontSize: 30, fontWeight: "300" },
  moduleScreen: { flex: 1, paddingTop: 12 },
  backButton: { alignSelf: "flex-start", paddingVertical: 10 },
  backText: { color: "#1f5148", fontSize: 15, fontWeight: "800" },
  moduleTitle: { color: "#1d2b2a", fontSize: 32, fontWeight: "700", letterSpacing: -0.8, marginBottom: 8 },
  loading: { alignItems: "center", flex: 1, gap: 12, justifyContent: "center", padding: 24 },
  errorCard: { backgroundColor: "#fff5f2", borderRadius: 14, marginTop: 18, padding: 16 },
  emptyCard: { backgroundColor: "#fbfaf7", borderColor: "#d9d7cf", borderRadius: 14, borderWidth: 1, marginTop: 18, padding: 18 },
  recordList: { gap: 10, paddingVertical: 18 },
  recordCard: { backgroundColor: "#fbfaf7", borderColor: "#d9d7cf", borderRadius: 14, borderWidth: 1, padding: 16 },
});
