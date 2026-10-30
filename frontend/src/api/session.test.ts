import { HttpResponse, http } from "msw";
import { describe, expect, it } from "vitest";
import { base64urlText } from "@/lib/auth/base64url";
import { getAccessToken, getRefreshToken, saveTokens } from "@/lib/auth/tokens";
import { server } from "@/test/server";
import { api } from "./client";
import { openEventStream } from "./eventStream";

/** An unsigned access token with the claims the interface reads (the backend is mocked). */
function accessToken(exp: number, sid = "s1"): string {
  const claims = { sub: "u1", org: null, sid, exp, name: "Ana", email: "ana@example.test", lang: null };
  return `${base64urlText('{"alg":"ES256"}')}.${base64urlText(JSON.stringify(claims))}.firma`;
}

const inAnHour = () => Math.floor(Date.now() / 1000) + 3600;

describe("API session", () => {
  it("signs every request and sends the access token", async () => {
    const seen: Headers[] = [];
    server.use(
      http.get("*/api/v1/me", ({ request }) => {
        seen.push(request.headers);
        return HttpResponse.json({});
      }),
    );
    await saveTokens(accessToken(inAnHour()), "r1");

    await api.GET("/api/v1/me");

    expect(seen[0]?.get("Authorization")).toBe(`DPoP ${getAccessToken()}`);
    expect(seen[0]?.get("DPoP")?.split(".")).toHaveLength(3);
  });

  it("refreshes an expired token once and retries the request", async () => {
    const fresh = accessToken(inAnHour(), "s1");
    let refreshes = 0;
    server.use(
      http.get("*/api/v1/me", ({ request }) =>
        request.headers.get("Authorization") === `DPoP ${fresh}`
          ? HttpResponse.json({ ok: true })
          : HttpResponse.json({ error: { code: "token_expired", message: "" } }, { status: 401 }),
      ),
      http.post("*/api/v1/auth/token/refresh", () => {
        refreshes += 1;
        return HttpResponse.json({ access_token: fresh, refresh_token: "r2" });
      }),
    );
    await saveTokens(accessToken(inAnHour(), "old"), "r1");

    const result = await api.GET("/api/v1/me");

    expect(result.data).toEqual({ ok: true });
    expect(refreshes).toBe(1);
    expect(await getRefreshToken()).toBe("r2");
  });

  it("renews before the request when the token is about to expire, once for many requests", async () => {
    let refreshes = 0;
    server.use(
      http.get("*/api/v1/me", () => HttpResponse.json({})),
      http.post("*/api/v1/auth/token/refresh", () => {
        refreshes += 1;
        return HttpResponse.json({ access_token: accessToken(inAnHour()), refresh_token: "r2" });
      }),
    );
    await saveTokens(accessToken(Math.floor(Date.now() / 1000) + 5), "r1");

    await Promise.all([api.GET("/api/v1/me"), api.GET("/api/v1/me"), api.GET("/api/v1/me")]);

    expect(refreshes).toBe(1);
  });

  it("forgets the session the backend closed", async () => {
    server.use(
      http.get("*/api/v1/me", () =>
        HttpResponse.json({ error: { code: "session_revoked", message: "" } }, { status: 401 }),
      ),
    );
    await saveTokens(accessToken(inAnHour()), "r1");

    await api.GET("/api/v1/me");

    expect(getAccessToken()).toBeNull();
    expect(await getRefreshToken()).toBeNull();
  });

  it("reads Server-Sent Events with the session headers", async () => {
    let authorization: string | null = null;
    server.use(
      http.get("*/api/v1/flights/bookings/b1/events", ({ request }) => {
        authorization = request.headers.get("Authorization");
        const body = new ReadableStream({
          start(controller) {
            const encoder = new TextEncoder();
            controller.enqueue(
              encoder.encode(': ping\n\nevent: status\nid: 1\ndata: {"status":"pending"}\n\n'),
            );
            controller.enqueue(encoder.encode('event: status\nid: 2\ndata: {"status":"confirmed"}\n\n'));
            controller.close();
          },
        });
        return new HttpResponse(body, { headers: { "Content-Type": "text/event-stream" } });
      }),
    );
    await saveTokens(accessToken(inAnHour()), "r1");
    const received: string[] = [];

    const stream = openEventStream(`${window.location.origin}/api/v1/flights/bookings/b1/events`);
    await new Promise<void>((resolve) => {
      stream.addEventListener("status", (event) => {
        received.push(JSON.parse(event.data).status);
        if (received.length === 2) resolve();
      });
    });
    stream.close();

    expect(received).toEqual(["pending", "confirmed"]);
    expect(authorization).toBe(`DPoP ${getAccessToken()}`);
  });
});
