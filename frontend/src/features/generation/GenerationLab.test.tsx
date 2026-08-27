import { afterEach, describe, expect, it, vi } from "vitest";
import { renderToStaticMarkup } from "react-dom/server";

import { ApiError, type ApiClient, type GenerationResponse, type UserResponse } from "../../api";
import { createPendingGeneration } from "../../state";
import {
  createGenerationRunner,
  isBillingConfirmationRequired,
  shouldShowFollowUpComposer,
  refreshGenerationEstimate,
  GenerationLab,
  FollowUpComposer,
  syncUserAfterGeneration,
} from "./GenerationLab";

const pending = createPendingGeneration(
  { chatbot_type: "basic", question: "광고", platform: "instagram" },
  { requires_confirmation: true, estimated_credits: 50 },
  "00000000-0000-0000-0000-000000000700",
);

const response: GenerationResponse = {
  generation_id: 7,
  status: "done",
  chatbot_type: "basic",
  result: null,
  usage: { plan: "paid", credits_used: 50 },
};

afterEach(() => {
  vi.useRealTimers();
});

describe("GenerationLab orchestration", () => {
  it("uses the wide canvas and primary composer structure for chatbot screens", () => {
    const html = renderToStaticMarkup(
      <GenerationLab
        api={{} as ApiClient}
        chatbotType="basic"
      />,
    );

    expect(html).toContain('class="generation-page generation-page--wide"');
    expect(html).toContain('class="card generation-card chat-generation-card chat-generation-card--primary"');
  });

  it("uses the full generation canvas for the follow-up composer", () => {
    const html = renderToStaticMarkup(
      <FollowUpComposer messages={[]} onSubmit={vi.fn()} />,
    );

    expect(html).toContain('class="card follow-up-card follow-up-card--wide"');
  });

  it("refreshes the authenticated user after generation without masking success", async () => {
    const user = { id: 1, daily_free_remaining: 9 } as UserResponse;
    const api = { me: vi.fn().mockResolvedValue(user) } as unknown as ApiClient;
    const onUserChanged = vi.fn();

    await syncUserAfterGeneration(api, onUserChanged);

    expect(api.me).toHaveBeenCalledTimes(1);
    expect(onUserChanged).toHaveBeenCalledWith(user);
  });

  it("ignores a user refresh failure after generation succeeds", async () => {
    const api = { me: vi.fn().mockRejectedValue(new Error("refresh failed")) } as unknown as ApiClient;

    await expect(syncUserAfterGeneration(api, vi.fn())).resolves.toBeUndefined();
  });

  it("deduplicates double confirmation with one Generate promise and key", async () => {
    const api = {
      generate: vi.fn().mockResolvedValue(response),
      waitingCopy: vi.fn().mockResolvedValue({
        id: 1,
        copy_text: "준비 중",
        industry: null,
      }),
    } as unknown as ApiClient;
    const runner = createGenerationRunner(api, vi.fn());

    const first = runner.run(pending);
    const second = runner.run(pending);

    expect(second).toBe(first);
    await expect(first).resolves.toEqual(response);
    expect(api.generate).toHaveBeenCalledTimes(1);
    expect(api.generate).toHaveBeenCalledWith(
      {
        chatbot_type: "basic",
        question: "광고",
        platform: "instagram",
        max_accepted_credits: 50,
      },
      "00000000-0000-0000-0000-000000000700",
    );
    runner.dispose();
  });

  it("stops waiting-copy refreshes when generation settles", async () => {
    vi.useFakeTimers();
    let resolveGenerate!: (value: GenerationResponse) => void;
    const generatePromise = new Promise<GenerationResponse>((resolve) => {
      resolveGenerate = resolve;
    });
    const api = {
      generate: vi.fn().mockReturnValue(generatePromise),
      waitingCopy: vi.fn().mockResolvedValue({
        id: 2,
        copy_text: "문구를 다듬는 중",
        industry: "카페",
      }),
    } as unknown as ApiClient;
    const onWaitingCopy = vi.fn();
    const runner = createGenerationRunner(api, onWaitingCopy, 1_000);

    const task = runner.run(pending);
    await vi.advanceTimersByTimeAsync(2_100);
    expect(api.waitingCopy).toHaveBeenCalledTimes(3);
    expect(api.generate).toHaveBeenCalledTimes(1);

    resolveGenerate(response);
    await task;
    const callsAfterSettle = vi.mocked(api.waitingCopy).mock.calls.length;
    await vi.advanceTimersByTimeAsync(3_000);

    expect(api.waitingCopy).toHaveBeenCalledTimes(callsAfterSettle);
    runner.dispose();
  });

  it("keeps waiting-copy refreshes at a calm default cadence", async () => {
    vi.useFakeTimers();
    let resolveGenerate!: (value: GenerationResponse) => void;
    const generatePromise = new Promise<GenerationResponse>((resolve) => {
      resolveGenerate = resolve;
    });
    const api = {
      generate: vi.fn().mockReturnValue(generatePromise),
      waitingCopy: vi.fn().mockResolvedValue({
        id: 3,
        copy_text: "준비 중",
        industry: "카페",
      }),
    } as unknown as ApiClient;
    const runner = createGenerationRunner(api, vi.fn());

    const task = runner.run(pending);
    expect(api.waitingCopy).toHaveBeenCalledTimes(1);

    await vi.advanceTimersByTimeAsync(14_999);
    expect(api.waitingCopy).toHaveBeenCalledTimes(1);

    await vi.advanceTimersByTimeAsync(1);
    expect(api.waitingCopy).toHaveBeenCalledTimes(2);

    resolveGenerate(response);
    await task;
    runner.dispose();
  });

  it("creates a fresh estimate action and key after billing confirmation changes", async () => {
    const api = {
      estimate: vi.fn().mockResolvedValue({
        requires_confirmation: true,
        estimated_credits: 60,
        current_credits: 100,
        credits_after: 40,
      }),
    } as unknown as ApiClient;

    const action = await refreshGenerationEstimate(
      api,
      pending,
      () => "00000000-0000-0000-0000-000000000701",
    );

    expect(action.kind).toBe("confirm");
    expect(action.pending.idempotencyKey).toBe(
      "00000000-0000-0000-0000-000000000701",
    );
    expect(action.pending.estimate.estimated_credits).toBe(60);
    expect(api.estimate).toHaveBeenCalledWith(pending.estimatePayload);
  });

  it("recognizes only the billing-confirmation 409 for re-estimate", () => {
    expect(
      isBillingConfirmationRequired(
        new ApiError(409, { reason: "billing_confirmation_required" }),
      ),
    ).toBe(true);
    expect(isBillingConfirmationRequired(new ApiError(409, { reason: "other" }))).toBe(
      false,
    );
    expect(isBillingConfirmationRequired(new ApiError(422, {}))).toBe(false);
  });

  it("hides the follow-up composer for blocked generation results", () => {
    expect(
      shouldShowFollowUpComposer({
        generation_id: 10,
        status: "failed",
        chatbot_type: "consultant",
        result: {
          status: "blocked",
          action: "reask",
          reason: "정보 부족",
          message: "추가 정보가 필요합니다.",
        },
        usage: { plan: "free", credits_used: 0 },
      }),
    ).toBe(false);
    expect(shouldShowFollowUpComposer({
      ...response,
      result: { status: "ok" },
    })).toBe(true);
  });
});
