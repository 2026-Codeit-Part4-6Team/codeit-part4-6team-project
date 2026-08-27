import { describe, expect, it, vi } from "vitest";

import { createIdempotencyKey } from "./requestId";

const uuidV4Pattern =
  /^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/;

describe("createIdempotencyKey", () => {
  it("uses randomUUID when the secure-context API is available", () => {
    const randomUUID = vi.fn(() => "11111111-1111-4111-8111-111111111111");
    const randomValues = vi.fn();

    const result = createIdempotencyKey({ randomUUID, getRandomValues: randomValues } as unknown as Crypto);

    expect(result).toBe("11111111-1111-4111-8111-111111111111");
    expect(randomUUID).toHaveBeenCalledOnce();
    expect(randomValues).not.toHaveBeenCalled();
  });

  it("generates an RFC 4122 v4 UUID with getRandomValues over HTTP", () => {
    const randomValues = vi.fn((bytes: Uint8Array) => {
      bytes.fill(0);
      return bytes;
    });

    const result = createIdempotencyKey({ getRandomValues: randomValues } as unknown as Crypto);

    expect(result).toMatch(uuidV4Pattern);
    expect(result).toBe("00000000-0000-4000-8000-000000000000");
    expect(randomValues).toHaveBeenCalledOnce();
    expect(randomValues.mock.calls[0]?.[0]).toHaveLength(16);
  });
});
