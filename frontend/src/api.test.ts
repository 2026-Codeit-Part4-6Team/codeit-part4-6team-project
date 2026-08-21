import { describe, expect, it, vi } from "vitest";

import { ApiClient, ApiError } from "./api";

describe("ApiClient", () => {
  it("sends registration payload and accepts an empty logout response", async () => {
    const fetcher = vi
      .fn<typeof fetch>()
      .mockResolvedValueOnce(
        new Response(JSON.stringify({ id: 1, username: "owner" }), { status: 201 }),
      )
      .mockResolvedValueOnce(new Response(null, { status: 204 }));
    const api = new ApiClient("/api", fetcher);
    const payload = {
      username: "owner",
      password: "safe-password",
      name: null,
      email: null,
      business_name: "코드잇 카페",
      business_type: "카페",
      address: "서울 강남구 테헤란로 1",
      address_detail: null,
    };

    await api.register(payload);
    await expect(api.logout()).resolves.toEqual({});

    expect(fetcher.mock.calls[0]?.[0]).toBe("/api/auth/register");
    expect(JSON.parse(String(fetcher.mock.calls[0]?.[1]?.body))).toEqual(payload);
    expect(fetcher.mock.calls[1]?.[0]).toBe("/api/auth/logout");
  });

  it("uses the default browser fetch without changing its receiver", async () => {
    const originalFetch = globalThis.fetch;
    globalThis.fetch = vi.fn(function (this: typeof globalThis) {
      if (this !== globalThis) {
        throw new TypeError("Illegal invocation");
      }
      return Promise.resolve(
        new Response(JSON.stringify({ id: 1, username: "owner" }), { status: 200 }),
      );
    }) as typeof fetch;

    try {
      const api = new ApiClient();
      await expect(api.me()).resolves.toMatchObject({ username: "owner" });
    } finally {
      globalThis.fetch = originalFetch;
    }
  });

  it("uses browser credentials for login and estimate", async () => {
    const fetcher = vi
      .fn<typeof fetch>()
      .mockResolvedValueOnce(new Response(JSON.stringify({ id: 1, username: "owner" }), { status: 200 }))
      .mockResolvedValueOnce(
        new Response(
          JSON.stringify({
            is_free: true,
            free_remaining: 9,
            estimated_credits: 50,
            current_credits: 100,
            credits_after: 100,
            requires_confirmation: false,
          }),
          { status: 200 },
        ),
      );
    const api = new ApiClient("/api", fetcher);

    await api.login({ username: "owner", password: "safe-password" });
    await api.estimate({ chatbot_type: "basic", question: "광고", platform: "instagram" });

    expect(fetcher.mock.calls[0]?.[1]?.credentials).toBe("include");
    expect(fetcher.mock.calls[1]?.[1]?.credentials).toBe("include");
  });

  it("sends an Idempotency-Key with generate", async () => {
    const fetcher = vi.fn<typeof fetch>().mockResolvedValue(
      new Response(
        JSON.stringify({
          generation_id: 7,
          status: "done",
          chatbot_type: "basic",
          result: null,
          usage: { plan: "free", credits_used: 0 },
        }),
        { status: 200 },
      ),
    );
    const api = new ApiClient("/api", fetcher);

    await api.generate(
      {
        chatbot_type: "basic",
        question: "광고",
        platform: "instagram",
        max_accepted_credits: 0,
      },
      "00000000-0000-0000-0000-000000000123",
    );

    const headers = new Headers(fetcher.mock.calls[0]?.[1]?.headers);
    expect(headers.get("Idempotency-Key")).toBe("00000000-0000-0000-0000-000000000123");
  });

  it("preserves status and parsed detail in ApiError", async () => {
    const fetcher = vi.fn<typeof fetch>().mockResolvedValue(
      new Response(JSON.stringify({ detail: { required: 50, current: 10 } }), { status: 402 }),
    );
    const api = new ApiClient("/api", fetcher);

    await expect(
      api.estimate({ chatbot_type: "basic", question: "광고", platform: "banner" }),
    ).rejects.toEqual(new ApiError(402, { required: 50, current: 10 }));
  });

  it("serializes the selected proposal for publish", async () => {
    const fetcher = vi.fn<typeof fetch>().mockResolvedValue(
      new Response(
        JSON.stringify({
          generation_id: 7,
          status: "published",
          hitl_approved: true,
          proposal_index: 1,
        }),
        { status: 200 },
      ),
    );
    const api = new ApiClient("/api", fetcher);

    await api.publishGeneration(7, { proposal_index: 1, image_b64: null });

    expect(fetcher.mock.calls[0]?.[0]).toBe("/api/generations/7/publish");
    expect(fetcher.mock.calls[0]?.[1]?.method).toBe("POST");
    expect(fetcher.mock.calls[0]?.[1]?.body).toBe(
      JSON.stringify({ proposal_index: 1, image_b64: null }),
    );
  });

  it("requests the latest waiting copy", async () => {
    const fetcher = vi.fn<typeof fetch>().mockResolvedValue(
      new Response(
        JSON.stringify({ id: 4, copy_text: "곧 완성됩니다.", industry: null }),
        { status: 200 },
      ),
    );
    const api = new ApiClient("/api", fetcher);

    await expect(api.waitingCopy()).resolves.toEqual({
      id: 4,
      copy_text: "곧 완성됩니다.",
      industry: null,
    });
    expect(fetcher.mock.calls[0]?.[0]).toBe("/api/waiting-copies");
    expect(fetcher.mock.calls[0]?.[1]?.method).toBe("GET");
  });
});
