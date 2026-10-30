import { base64urlText } from "@/lib/auth/base64url";
import { saveTokens } from "@/lib/auth/tokens";

/** Claims of the test user's access token. */
export const TEST_USER = {
  sub: "00000000-0000-4000-8000-000000000001",
  org: null,
  sid: "00000000-0000-4000-8000-0000000000aa",
  // Far in the future: some tests freeze the clock at the fixtures' date.
  exp: 4_102_444_800,
  name: "Pepe Perez",
  email: "pepe.perez@ejemplo.com",
  lang: null,
};

/** `GET /me` of the test user, as the backend answers it: without phone unless a test says so. */
export const TEST_ME = {
  id: TEST_USER.sub,
  email: TEST_USER.email,
  display_name: TEST_USER.name,
  organization: null,
  has_password: true,
  phone_number: null as string | null,
  language: null,
  traveller_profile: null as {
    title: "ms" | "mr" | "mrs" | "miss" | "dr";
    born_on: string;
    gender: "m" | "f";
  } | null,
  session_id: TEST_USER.sid,
};

/** An access token with the test user's claims; the backend is mocked, so it isn't signed. */
export function testAccessToken(claims: Partial<typeof TEST_USER> = {}): string {
  return `${base64urlText('{"alg":"ES256","typ":"at+jwt"}')}.${base64urlText(JSON.stringify({ ...TEST_USER, ...claims }))}.firma`;
}

/** Signs the test user in on this device, as if they had just entered. */
export async function signInForTests(claims: Partial<typeof TEST_USER> = {}): Promise<void> {
  await saveTokens(testAccessToken(claims), "refresh-de-prueba");
}
