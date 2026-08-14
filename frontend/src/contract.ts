export type ChatbotType = "basic" | "consultant";
export type Platform = "instagram" | "banner";

export type EstimatePayload = {
  chatbot_type: ChatbotType;
  question: string;
  platform?: Platform;
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
): EstimatePayload {
  const normalizedQuestion = question.trim();
  if (!normalizedQuestion) {
    throw new Error("질문을 입력해 주세요.");
  }
  const payload: EstimatePayload = {
    chatbot_type: chatbotType,
    question: normalizedQuestion,
  };
  if (chatbotType === "basic") {
    payload.platform = platform;
  }
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
