import {
  acceptedCredits,
  buildGeneratePayload,
  type EstimatePayload,
  type EstimateResponse,
  type GeneratePayload,
} from "./contract";

export type PendingGeneration = {
  estimatePayload: EstimatePayload;
  estimate: EstimateResponse;
  idempotencyKey: string;
};

export function createPendingGeneration(
  estimatePayload: EstimatePayload,
  estimate: EstimateResponse,
  idempotencyKey: string,
): PendingGeneration {
  return { estimatePayload: { ...estimatePayload }, estimate: { ...estimate }, idempotencyKey };
}

export function generationPayload(pending: PendingGeneration): GeneratePayload {
  return buildGeneratePayload(pending.estimatePayload, acceptedCredits(pending.estimate));
}

export function apiErrorMessage(statusCode: number, detail: unknown): string {
  if (statusCode === 401) {
    return "로그인이 만료되었습니다. 다시 로그인해 주세요.";
  }
  if (statusCode === 402 && typeof detail === "object" && detail !== null) {
    const credit = detail as { required?: number; current?: number };
    return `Credit이 부족합니다. 필요 ${credit.required}, 현재 ${credit.current}`;
  }
  if (statusCode === 409) {
    return "요청 상태가 변경되었습니다. 예상 사용량을 다시 확인해 주세요.";
  }
  if (statusCode === 422) {
    return "입력값을 확인해 주세요.";
  }
  if (statusCode >= 500) {
    return "서버 연결이 불안정합니다. 잠시 후 다시 시도해 주세요.";
  }
  return "요청을 처리하지 못했습니다.";
}
