import { describe, expect, it, vi } from "vitest";

import { createIdempotencyKey } from "./requestId";

describe("createIdempotencyKey", () => {
  it("uses randomUUID when the secure-context API is available", () => {
    const randomUUID = vi.fn(() => "11111111-1111-4111-8111-111111111111");
    const randomValues = vi.fn();

    expect(createIdempotencyKey({ randomUUID, getRandomValues: randomValues } as unknown as Crypto)).toBe(
      "11111111-1111-4111-8111-111111111111",
    );
    expect(randomUUID).toHaveBeenCalledOnce();
    expect(randomValues).not.toHaveBeenCalled();
  });

  it("builds an RFC 4122 key when randomUUID is unavailable on HTTP", () => {
    const randomValues = vi.fn((bytes: Uint8Array) => bytes.fill(0));

    const result = createIdempotencyKey({ getRandomValues: randomValues } as unknown as Crypto);

    expect(result).toMatch(
      /^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/,
    );
    expect(randomValues).toHaveBeenCalledOnce();
  });
});
