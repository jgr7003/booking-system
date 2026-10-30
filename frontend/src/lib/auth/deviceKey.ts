import { base64url } from "./base64url";
import { readValue, writeValue } from "./storage";

/**
 * The key pair that identifies this browser (03-usuarios-y-acceso.md §11). The private key is
 * created **non-extractable**: JavaScript can sign with it but never read or copy it, so a token
 * copied to another device is useless without it.
 */
export interface DeviceKey {
  privateKey: CryptoKey;
  /** Public key as a JWK (`kty`, `crv`, `x`, `y`), sent in every DPoP proof. */
  publicJwk: JsonWebKey;
  /** JWK SHA-256 thumbprint (RFC 7638): the identity of the device for the backend. */
  thumbprint: string;
}

const STORAGE_KEY = "device-key";
let current: Promise<DeviceKey> | null = null;

async function thumbprintOf(jwk: JsonWebKey): Promise<string> {
  // RFC 7638: the required members, in lexicographic order, without spaces.
  const canonical = JSON.stringify({ crv: jwk.crv, kty: jwk.kty, x: jwk.x, y: jwk.y });
  return base64url(await crypto.subtle.digest("SHA-256", new TextEncoder().encode(canonical)));
}

async function load(): Promise<DeviceKey> {
  const stored = await readValue<{ privateKey: CryptoKey; publicJwk: JsonWebKey }>(STORAGE_KEY);
  if (stored) return { ...stored, thumbprint: await thumbprintOf(stored.publicJwk) };
  const pair = await crypto.subtle.generateKey({ name: "ECDSA", namedCurve: "P-256" }, false, [
    "sign",
    "verify",
  ]);
  const exported = await crypto.subtle.exportKey("jwk", pair.publicKey);
  const publicJwk: JsonWebKey = { kty: exported.kty, crv: exported.crv, x: exported.x, y: exported.y };
  await writeValue(STORAGE_KEY, { privateKey: pair.privateKey, publicJwk });
  return { privateKey: pair.privateKey, publicJwk, thumbprint: await thumbprintOf(publicJwk) };
}

/** The key of this device, created the first time it's needed. */
export function getDeviceKey(): Promise<DeviceKey> {
  current ??= load().catch((error) => {
    current = null;
    throw error;
  });
  return current;
}

/** Forgets the cached key (tests). */
export function resetDeviceKeyCache(): void {
  current = null;
}
