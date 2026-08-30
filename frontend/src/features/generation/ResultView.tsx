import { useState } from "react";

import type { GenerationResponse } from "../../api";
import type { Platform } from "../../contract";
import { ResultCards, type ProposalIndex } from "./ResultCards";

type ResultViewProps = {
  response: GenerationResponse;
  platform?: Platform | null;
  publishedProposalIndex?: ProposalIndex | null;
  publishing?: boolean;
  onPublish: (index: ProposalIndex, imageB64: string | null) => void | Promise<void>;
  onRegenerate: () => void;
  onSuggestedChip?: (chip: string) => void;
  onStrategyToAd?: (sourceGenId: number, strategySummary: string) => void;
  onClarification?: (value: string) => void | Promise<void>;
};

type PolicyReason =
  | "illegal_or_injection"
  | "need_clarification"
  | "insufficient_info"
  | "prohibited_item"
  | "regulation_risk"
  | "sensitive_leak"
  | "content_policy";

const clarificationReasons = new Set<PolicyReason>([
  "illegal_or_injection",
  "need_clarification",
  "insufficient_info",
]);

function resultValue(response: GenerationResponse, key: string): unknown {
  return response.result && typeof response.result === "object"
    ? response.result[key]
    : undefined;
}

function resultText(response: GenerationResponse, key: string): string | null {
  const value = resultValue(response, key);
  return typeof value === "string" && value.trim().length > 0 ? value : null;
}

function policyReason(response: GenerationResponse): PolicyReason | null {
  const reason = resultText(response, "reason");
  return reason && [
    "illegal_or_injection",
    "need_clarification",
    "insufficient_info",
    "prohibited_item",
    "regulation_risk",
    "sensitive_leak",
    "content_policy",
  ].includes(reason)
    ? (reason as PolicyReason)
    : null;
}

function policyHeading(reason: PolicyReason | null): string {
  if (reason === "illegal_or_injection") return "질문을 다시 입력해 주세요";
  if (clarificationReasons.has(reason as PolicyReason)) return "조금만 더 알려주세요";
  if (reason === "regulation_risk") return "대안 표현을 확인해 주세요";
  if (reason === "prohibited_item" || reason === "sensitive_leak") return "생성을 중단했어요";
  return "생성 결과를 확인해 주세요";
}

function alternativeText(response: GenerationResponse): string | null {
  const direct = resultText(response, "alternative") ?? resultText(response, "suggested_copy");
  if (direct) return direct;
  const alternatives = resultValue(response, "alternatives");
  if (Array.isArray(alternatives)) {
    const first = alternatives.find((value): value is string => typeof value === "string" && value.trim().length > 0);
    return first ?? null;
  }
  return null;
}

export function isSuccessfulGeneration(response: GenerationResponse): boolean {
  return response.status === "done" && response.result?.status === "ok";
}

function nonSuccessMessage(response: GenerationResponse): string {
  const message = response.result?.message;
  if (typeof message === "string" && message.trim().length > 0) {
    return message;
  }
  return "생성 결과를 표시할 수 없습니다. 입력 내용을 확인해 주세요.";
}

function ClarificationForm({ onSubmit }: { onSubmit: (value: string) => void | Promise<void> }) {
  const [value, setValue] = useState("");
  return (
    <form
      className="blocked-result-form"
      onSubmit={(event) => {
        event.preventDefault();
        const trimmed = value.trim();
        if (!trimmed) return;
        void onSubmit(trimmed);
        setValue("");
      }}
    >
      <label htmlFor="blocked-clarification">추가 답변</label>
      <textarea
        id="blocked-clarification"
        value={value}
        onChange={(event) => setValue(event.target.value)}
        placeholder="예: 여름 신메뉴를 20대 고객에게 알리고 싶어요."
        rows={3}
      />
      <button type="submit" className="primary" disabled={!value.trim()}>
        이 내용으로 이어서 만들기
      </button>
    </form>
  );
}

function PolicyResult({
  response,
  onRegenerate,
  onClarification,
}: {
  response: GenerationResponse;
  onRegenerate: () => void;
  onClarification?: (value: string) => void | Promise<void>;
}) {
  const reason = policyReason(response);
  const showClarification = reason !== null && clarificationReasons.has(reason);
  const alternative = reason === "regulation_risk" ? alternativeText(response) : null;
  return (
    <section className={`card blocked-result blocked-result--${reason ?? "unknown"}`} role="alert">
      <div className="blocked-result-heading">
        <span className="blocked-result-icon" aria-hidden="true">{showClarification ? "?" : reason === "regulation_risk" ? "✦" : "!"}</span>
        <div>
          <p className="kicker">검증 결과 안내</p>
          <h2>{policyHeading(reason)}</h2>
          <p>{nonSuccessMessage(response)}</p>
        </div>
      </div>
      {alternative && <p className="blocked-result-alternative"><strong>추천 대안</strong>{alternative}</p>}
      {showClarification && onClarification && <ClarificationForm onSubmit={onClarification} />}
      {reason === "regulation_risk" && (
        <button type="button" className="action-button action-button-secondary" onClick={onRegenerate}>
          <span className="action-button-icon" aria-hidden="true">↻</span>
          <span>다시 만들기</span>
        </button>
      )}
    </section>
  );
}

export function ResultView({
  response,
  platform = null,
  publishedProposalIndex = null,
  publishing = false,
  onPublish,
  onRegenerate,
  onSuggestedChip,
  onStrategyToAd,
  onClarification,
}: ResultViewProps) {
  const [selectedProposalIndex, setSelectedProposalIndex] =
    useState<ProposalIndex | null>(null);

  if (!isSuccessfulGeneration(response)) {
    return <PolicyResult response={response} onRegenerate={onRegenerate} onClarification={onClarification} />;
  }

  const proposals = Array.isArray(response.result?.proposals)
    ? response.result.proposals
    : [];
  const selected =
    selectedProposalIndex === null
      ? null
      : (proposals[selectedProposalIndex] as { image_b64?: unknown } | undefined);
  const selectedImage =
    typeof selected?.image_b64 === "string" ? selected.image_b64 : null;

  return (
    <>
      {publishedProposalIndex !== null && (
        <p className="publish-success" role="status">
          게시 승인 완료
        </p>
      )}
      <ResultCards
        response={response}
        platform={platform}
        onSuggestedChip={onSuggestedChip}
        onStrategyToAd={onStrategyToAd}
        onSelectProposal={setSelectedProposalIndex}
        selectedProposalIndex={selectedProposalIndex}
        publishedProposalIndex={publishedProposalIndex}
      />
      <div className="result-actions" aria-label="생성 결과 작업">
        <div className="result-action-copy">
          <span>다음 단계</span>
          <small>{publishedProposalIndex !== null ? "게시 승인이 완료되었습니다." : "제안을 선택하거나 새로 만들어 보세요."}</small>
        </div>
        <div className="result-action-buttons">
        {response.chatbot_type === "basic" && publishedProposalIndex === null && (
          <button
            type="button"
            className="action-button action-button-primary publish-action"
            disabled={selectedProposalIndex === null || publishing}
            onClick={() => {
              if (selectedProposalIndex !== null) {
                void onPublish(selectedProposalIndex, selectedImage);
              }
            }}
          >
            <span className="action-button-icon" aria-hidden="true">{publishing ? "…" : "✓"}</span>
            <span>{publishing ? "승인 중…" : "선택한 제안 게시 승인"}</span>
          </button>
        )}
        <button type="button" className="action-button action-button-secondary regenerate-action" onClick={onRegenerate}>
          <span className="action-button-icon" aria-hidden="true">↻</span>
          <span>다시 생성</span>
        </button>
        </div>
      </div>
    </>
  );
}
