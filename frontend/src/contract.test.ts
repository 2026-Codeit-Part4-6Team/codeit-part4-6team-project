import { describe, expect, it } from "vitest";

import {
  acceptedCredits,
  buildEstimatePayload,
  buildGeneratePayload,
} from "./contract";

describe("generation contract", () => {
  it("includes platform only for a Basic estimate", () => {
    expect(buildEstimatePayload("basic", "  여름 음료 광고  ", "instagram")).toEqual({
      chatbot_type: "basic",
      question: "여름 음료 광고",
      platform: "instagram",
      extra: {
        purpose: null,
        price_range: null,
        target_age: null,
        strength: null,
        clarification: null,
      },
    });
    expect(buildEstimatePayload("consultant", "상권 전략", "banner")).toEqual({
      chatbot_type: "consultant",
      question: "상권 전략",
      platform: null,
      extra: {
        purpose: null,
        price_range: null,
        target_age: null,
        strength: null,
        clarification: null,
      },
    });
  });

  it("rejects a blank question", () => {
    expect(() => buildEstimatePayload("basic", "   ", "instagram")).toThrow("질문");
  });

  it("adds the accepted credit limit to the generate payload", () => {
    const estimatePayload = {
      chatbot_type: "basic" as const,
      question: "신메뉴 광고",
      platform: "banner" as const,
    };
    expect(buildGeneratePayload(estimatePayload, 50)).toEqual({
      ...estimatePayload,
      max_accepted_credits: 50,
    });
  });

  it("accepts estimated credits only when confirmation is required", () => {
    expect(acceptedCredits({ requires_confirmation: false, estimated_credits: 50 })).toBe(0);
    expect(acceptedCredits({ requires_confirmation: true, estimated_credits: 50 })).toBe(50);
  });
});
