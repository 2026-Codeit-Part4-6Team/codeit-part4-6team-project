export type ChatbotType = "basic" | "consultant";
export type Platform = "instagram" | "banner";
export type GenerateExtra = {
  purpose: string | null;
  price_range: string | null;
  target_age: string | null;
  strength: string | null;
  clarification: string | null;
};

export type EstimatePayload = {
  chatbot_type: ChatbotType;
  question: string;
  platform?: Platform | null;
  extra?: GenerateExtra;
};

export type GeneratePayload = EstimatePayload & {
  max_accepted_credits: number;
};

export type EstimateResponse = {
  is_free?: boolean;
  free_remaining?: number;
  estimated_credits: number;
  current_credits?: number;
  credits_after?: number;
  requires_confirmation: boolean;
};

export function buildEstimatePayload(
  chatbotType: ChatbotType,
  question: string,
  platform: Platform,
  extra: Partial<GenerateExtra> = {},
): EstimatePayload {
  const normalizedQuestion = question.trim();
  if (!normalizedQuestion) {
    throw new Error("질문을 입력해 주세요.");
  }
  const payload: EstimatePayload = {
    chatbot_type: chatbotType,
    question: normalizedQuestion,
    extra: {
      purpose: extra.purpose ?? null,
      price_range: extra.price_range ?? null,
      target_age: extra.target_age ?? null,
      strength: extra.strength ?? null,
      clarification: extra.clarification ?? null,
    },
  };
  payload.platform = chatbotType === "basic" ? platform : null;
  return payload;
}

export function buildGeneratePayload(
  estimatePayload: EstimatePayload,
  maxAcceptedCredits: number,
): GeneratePayload {
  return {
    ...estimatePayload,
    max_accepted_credits: maxAcceptedCredits,
  };
}

export function acceptedCredits(estimate: EstimateResponse): number {
  return estimate.requires_confirmation ? estimate.estimated_credits : 0;
}
