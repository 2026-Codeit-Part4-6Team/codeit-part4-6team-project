import { describe, expect, it } from "vitest";

import {
  apiErrorMessage,
  createFollowUpMessage,
  createPendingGeneration,
  generationPayload,
  nextGenerationAction,
  withClarification,
} from "./state";

describe("generation state", () => {
  it("reuses its key and accepts estimated paid credits", () => {
    const pending = createPendingGeneration(
      { chatbot_type: "basic", question: "광고", platform: "instagram" },
      { requires_confirmation: true, estimated_credits: 50 },
      "00000000-0000-0000-0000-000000000456",
    );

    expect(pending.idempotencyKey).toBe("00000000-0000-0000-0000-000000000456");
    expect(generationPayload(pending)).toEqual({
      chatbot_type: "basic",
      question: "광고",
      platform: "instagram",
      max_accepted_credits: 50,
    });
  });

  it("starts free generation immediately and pauses paid generation for consent", () => {
    const payload = {
      chatbot_type: "basic" as const,
      question: "광고",
      platform: "instagram" as const,
    };

    const free = nextGenerationAction(
      { requires_confirmation: false, estimated_credits: 50 },
      payload,
      "key-free",
    );
    const paid = nextGenerationAction(
      { requires_confirmation: true, estimated_credits: 50 },
      payload,
      "key-paid",
    );

    expect(free.kind).toBe("generate");
    expect(generationPayload(free.pending).max_accepted_credits).toBe(0);
    expect(paid.kind).toBe("confirm");
    expect(generationPayload(paid.pending).max_accepted_credits).toBe(50);
  });

  it("distinguishes auth, credit, validation, and server errors", () => {
    expect(apiErrorMessage(401, {})).toBe("로그인이 만료되었습니다. 다시 로그인해 주세요.");
    expect(apiErrorMessage(402, { required: 50, current: 10 })).toBe(
      "Credit이 부족합니다. 필요 50, 현재 10",
    );
    expect(apiErrorMessage(422, {})).toBe("입력값을 확인해 주세요.");
    expect(apiErrorMessage(503, {})).toBe(
      "서버 연결이 불안정합니다. 잠시 후 다시 시도해 주세요.",
    );
  });

  it("creates follow-up messages for the generation conversation", () => {
    expect(createFollowUpMessage("user", "더 캐주얼하게", "m1")).toEqual({
      id: "m1",
      role: "user",
      content: "더 캐주얼하게",
    });
  });

  it("adds clarification to the next generation request without dropping other fields", () => {
    expect(withClarification({
      purpose: "신메뉴 홍보",
      price_range: null,
      target_age: "20대",
      strength: null,
      clarification: null,
    }, "더 캐주얼하게")).toEqual({
      purpose: "신메뉴 홍보",
      price_range: null,
      target_age: "20대",
      strength: null,
      clarification: "더 캐주얼하게",
    });
  });
});
