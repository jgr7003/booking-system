import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { clearSession, loadStoredSession, saveTokens } from "@/lib/auth/tokens";
import { ApiError, api, type Schemas, unwrap } from "./client";
import { freshAccessToken } from "./session";

/** Sign in, accounts and device sessions (03-usuarios-y-acceso.md §13). */

export type AuthMethods = Schemas["AuthMethodsResponse"];
export type TokenResponse = Schemas["TokenResponse"];
export type AccountNotFound = Schemas["AccountNotFoundResponse"];
export type Me = Schemas["MeResponse"];
export type DeviceSession = Schemas["DeviceSessionResponse"];
export type PasswordLink = Schemas["PasswordLinkResponse"];

export const authKeys = {
  methods: ["auth", "methods"] as const,
  me: ["auth", "me"] as const,
  sessions: ["auth", "sessions"] as const,
  passwordLink: (token: string) => ["auth", "password-link", token] as const,
};

/** Keeps the tokens of a new session of this device. */
async function signedIn(tokens: TokenResponse): Promise<TokenResponse> {
  await saveTokens(tokens.access_token, tokens.refresh_token);
  return tokens;
}

/**
 * Restores the session of this device when the app opens: if a refresh token is stored, asks a
 * new access token, so the interface knows who the user is.
 */
export async function bootstrapSession(): Promise<void> {
  await loadStoredSession();
  await freshAccessToken();
}

export function useAuthMethods() {
  return useQuery({
    queryKey: authKeys.methods,
    queryFn: async () => unwrap(await api.GET("/api/v1/auth/methods")),
    staleTime: 5 * 60_000,
  });
}

export async function lookupEmail(email: string) {
  return unwrap(await api.POST("/api/v1/auth/password/lookup", { body: { email } }));
}

export async function loginWithPassword(email: string, password: string) {
  return signedIn(unwrap(await api.POST("/api/v1/auth/password/login", { body: { email, password } })));
}

export interface SignupInput {
  email: string;
  display_name: string;
  password: string;
  phone_number?: string | null;
}

export async function signUp(input: SignupInput) {
  const result = await api.POST("/api/v1/auth/password/signup", { body: input });
  if (!result.response.ok) unwrap(result);
}

export async function verifyEmail(token: string) {
  return signedIn(unwrap(await api.POST("/api/v1/auth/email/verify", { body: { token } })));
}

export async function forgotPassword(email: string) {
  const result = await api.POST("/api/v1/auth/password/forgot", { body: { email } });
  if (!result.response.ok) unwrap(result);
}

export async function setPassword(token: string, password: string) {
  const result = await api.POST("/api/v1/auth/password/set", { body: { token, password } });
  if (!result.response.ok) unwrap(result);
}

export function usePasswordLink(token: string) {
  return useQuery({
    queryKey: authKeys.passwordLink(token),
    queryFn: async () => unwrap(await api.POST("/api/v1/auth/password/link", { body: { token } })),
    enabled: token.length > 0,
    retry: false,
  });
}

/** Starts a sign in through a provider; returns the URL the browser opens. */
export async function authorizeWithProvider(
  provider: string,
  returnTo: string | null,
  anotherAccount = false,
) {
  const body = { return_to: returnTo, another_account: anotherAccount };
  const result = unwrap(
    await api.POST("/api/v1/auth/oidc/{provider}/authorize", { params: { path: { provider } }, body }),
  );
  return result.authorization_url;
}

export type CallbackResult = { status: "signed_in"; tokens: TokenResponse } | AccountNotFound;

/** Finishes a sign in with what the provider sent back. */
export async function finishProviderSignIn(
  provider: string,
  code: string,
  state: string,
): Promise<CallbackResult> {
  const result = unwrap(
    await api.POST("/api/v1/auth/oidc/{provider}/callback", {
      params: { path: { provider } },
      body: { code, state },
    }),
  ) as CallbackResult;
  if (result.status === "signed_in") await signedIn(result.tokens);
  return result;
}

export async function getPendingSignup(attemptId: string) {
  return unwrap(
    await api.GET("/api/v1/auth/signup/pending/{attempt_id}", {
      params: { path: { attempt_id: attemptId } },
    }),
  );
}

export async function createPendingAccount(attemptId: string, phoneNumber: string | null) {
  return signedIn(
    unwrap(
      await api.POST("/api/v1/auth/signup/pending/{attempt_id}", {
        params: { path: { attempt_id: attemptId } },
        body: { phone_number: phoneNumber },
      }),
    ),
  );
}

export async function discardPendingSignup(attemptId: string) {
  await api.DELETE("/api/v1/auth/signup/pending/{attempt_id}", {
    params: { path: { attempt_id: attemptId } },
  });
}

/** The signed-in user, read fresh (no request without a session). */
export function useMe(enabled: boolean) {
  return useQuery({
    queryKey: authKeys.me,
    queryFn: async () => unwrap(await api.GET("/api/v1/me")),
    enabled,
    staleTime: 60_000,
  });
}

export function useDeviceSessions() {
  return useQuery({
    queryKey: authKeys.sessions,
    queryFn: async () => unwrap(await api.GET("/api/v1/me/sessions")).sessions,
  });
}

export function useCloseDeviceSession() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (sessionId: string) => {
      const result = await api.DELETE("/api/v1/me/sessions/{session_id}", {
        params: { path: { session_id: sessionId } },
      });
      if (!result.response.ok) unwrap(result);
    },
    onSuccess: () => queryClient.invalidateQueries({ queryKey: authKeys.sessions }),
  });
}

export function useCloseOtherSessions() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async () => {
      const result = await api.DELETE("/api/v1/me/sessions", { params: { query: { scope: "others" } } });
      if (!result.response.ok) unwrap(result);
    },
    onSuccess: () => queryClient.invalidateQueries({ queryKey: authKeys.sessions }),
  });
}

/** Signs this device out: the backend closes its session and the tokens are forgotten here. */
export async function signOut(): Promise<void> {
  try {
    await api.POST("/api/v1/auth/logout");
  } finally {
    await clearSession("signed_out");
  }
}

/** Whether an error of the API is the one answer of a failed sign in. */
export function isLoginFailed(error: unknown): boolean {
  return error instanceof ApiError && error.code === "login_failed";
}
