import { describe, expect, it, vi } from "vitest";

import { ApiClient, ApiError } from "./api";

describe("ApiClient", () => {
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
});
