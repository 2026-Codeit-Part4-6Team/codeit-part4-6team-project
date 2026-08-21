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
      <div className="result-actions">
        {response.chatbot_type === "basic" && publishedProposalIndex === null && (
          <button
            type="button"
            disabled={selectedProposalIndex === null || publishing}
            onClick={() => {
              if (selectedProposalIndex !== null) {
                void onPublish(selectedProposalIndex, selectedImage);
              }
            }}
          >
            {publishing ? "승인 중…" : "선택한 제안 게시 승인"}
          </button>
        )}
        <button type="button" className="secondary" onClick={onRegenerate}>
          다시 생성
        </button>
      </div>
    </>
  );
}
