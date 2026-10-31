import { base64url, base64urlText } from "./base64url";
import { getDeviceKey } from "./deviceKey";

/**
 * Builds a DPoP proof (RFC 9449): a short JWT, signed by the device key, that says which request
 * it is for. The backend refuses it for another method, URL or access token, or if it's reused.
 *
 * @param method HTTP method of the request.
 * @param url Full URL of the request; the query is left out (`htu`).
 * @param accessToken Access token sent with the request, if any: its hash goes in `ath`.
 */
export async function createDpopProof(method: string, url: string, accessToken?: string): Promise<string> {
  const key = await getDeviceKey();
  const target = new URL(url);
  const claims: Record<string, unknown> = {
    htm: method.toUpperCase(),
    htu: `${target.origin}${target.pathname}`,
    iat: Math.floor(Date.now() / 1000),
    jti: crypto.randomUUID(),
  };
  if (accessToken) {
    claims.ath = base64url(await crypto.subtle.digest("SHA-256", new TextEncoder().encode(accessToken)));
  }
  const header = { typ: "dpop+jwt", alg: "ES256", jwk: key.publicJwk };
  const signingInput = `${base64urlText(JSON.stringify(header))}.${base64urlText(JSON.stringify(claims))}`;
  // WebCrypto returns the raw `r || s` signature, which is exactly what ES256 in a JWS uses.
  const signature = await crypto.subtle.sign(
    { name: "ECDSA", hash: "SHA-256" },
    key.privateKey,
    new TextEncoder().encode(signingInput),
  );
  return `${signingInput}.${base64url(signature)}`;
}
