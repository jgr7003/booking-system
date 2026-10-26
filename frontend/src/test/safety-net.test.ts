import { describe, expect, it } from "vitest";

describe("test safety net", () => {
  it("a request without a mock fails instead of reaching the network", async () => {
    await expect(fetch(`${window.location.origin}/api/v1/not-mocked`)).rejects.toThrow();
  });
});
