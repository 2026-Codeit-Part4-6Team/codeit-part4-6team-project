import { useState } from "react";

import type { GenerationResponse } from "../../api";
import { ResultCards, type ProposalIndex } from "./ResultCards";

type ResultViewProps = {
  response: GenerationResponse;
  publishedProposalIndex?: ProposalIndex | null;
  publishing?: boolean;
  onPublish: (index: ProposalIndex, imageB64: string | null) => void | Promise<void>;
  onRegenerate: () => void;
  onSuggestedChip?: (chip: string) => void;
};

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

export function ResultView({
  response,
  publishedProposalIndex = null,
  publishing = false,
  onPublish,
  onRegenerate,
  onSuggestedChip,
}: ResultViewProps) {
  const [selectedProposalIndex, setSelectedProposalIndex] =
    useState<ProposalIndex | null>(null);

  if (!isSuccessfulGeneration(response)) {
    return (
      <section className="card blocked-result" role="alert">
        <p>{nonSuccessMessage(response)}</p>
      </section>
    );
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
        onSuggestedChip={onSuggestedChip}
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
