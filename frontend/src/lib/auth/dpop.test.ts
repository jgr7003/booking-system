import { describe, expect, it } from "vitest";
import { base64url, base64urlText, decodeBase64urlText } from "./base64url";
import { getDeviceKey } from "./deviceKey";
import { createDpopProof } from "./dpop";

function decodePart(part: string) {
  return JSON.parse(decodeBase64urlText(part)) as Record<string, unknown>;
}

function decodeSignature(part: string): Uint8Array<ArrayBuffer> {
  const padded = part
    .replace(/-/g, "+")
    .replace(/_/g, "/")
    .padEnd(Math.ceil(part.length / 4) * 4, "=");
  return Uint8Array.from(atob(padded), (c) => c.charCodeAt(0));
}

describe("DPoP proof", () => {
  it("names the request and carries the public key, never the private one", async () => {
    const proof = await createDpopProof("post", "http://localhost:5173/api/v1/me?x=1#y");
    const [header, claims] = proof.split(".").map((p, i) => (i < 2 ? decodePart(p) : p));

    expect(header).toMatchObject({ typ: "dpop+jwt", alg: "ES256" });
    expect(Object.keys((header as { jwk: object }).jwk).sort()).toEqual(["crv", "kty", "x", "y"]);
    expect(claims).toMatchObject({ htm: "POST", htu: "http://localhost:5173/api/v1/me" });
    expect((claims as { jti: string }).jti).toHaveLength(36);
    expect((claims as { ath?: string }).ath).toBeUndefined();
  });

  it("is signed by the device key", async () => {
    const proof = await createDpopProof("GET", "http://localhost:5173/api/v1/me");
    const [header = "", claims = "", signature = ""] = proof.split(".");
    const jwk = decodePart(header).jwk as JsonWebKey;
    const key = await crypto.subtle.importKey("jwk", jwk, { name: "ECDSA", namedCurve: "P-256" }, false, [
      "verify",
    ]);

    const valid = await crypto.subtle.verify(
      { name: "ECDSA", hash: "SHA-256" },
      key,
      decodeSignature(signature),
      new TextEncoder().encode(`${header}.${claims}`),
    );

    expect(valid).toBe(true);
  });

  it("binds the access token with its hash", async () => {
    const proof = await createDpopProof("GET", "http://localhost:5173/api/v1/me", "token-abc");
    const expected = base64url(await crypto.subtle.digest("SHA-256", new TextEncoder().encode("token-abc")));

    expect(decodePart(proof.split(".")[1] ?? "").ath).toBe(expected);
  });

  it("keeps one device key with a stable RFC 7638 thumbprint", async () => {
    const first = await getDeviceKey();
    const second = await getDeviceKey();
    const { crv, kty, x, y } = first.publicJwk;
    const canonical = JSON.stringify({ crv, kty, x, y });
    const digest = await crypto.subtle.digest("SHA-256", new TextEncoder().encode(canonical));

    expect(second.thumbprint).toBe(first.thumbprint);
    expect(first.thumbprint).toBe(base64url(digest));
    expect(first.privateKey.extractable).toBe(false);
  });

  it("encodes base64url without padding", () => {
    expect(base64urlText("??>")).toBe("Pz8-");
    expect(decodeBase64urlText("Pz8-")).toBe("??>");
  });
});
