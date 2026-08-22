import type { GenerationResponse } from "../../api";
import type { Platform } from "../../contract";

const actionMeta: Record<string, { label: string; visual: string }> = {
  menu: { label: "핵심 상품/서비스", visual: "✦" },
  promotion: { label: "프로모션", visual: "📣" },
  target: { label: "타깃 고객", visual: "👥" },
  other: { label: "추가 제안", visual: "＋" },
};

// 모델 enum은 사용자 문구가 아니므로 카드에서는 한국어 라벨과 시각 요소로 변환한다.

export type ProposalIndex = 0 | 1 | 2;

type ResultCardsProps = {
  response: GenerationResponse;
  platform?: Platform | null;
  onSuggestedChip?: (chip: string) => void;
  onStrategyToAd?: (sourceGenId: number, purpose: string) => void;
  onSelectProposal?: (index: ProposalIndex) => void;
  selectedProposalIndex?: ProposalIndex | null;
  publishedProposalIndex?: ProposalIndex | null;
};

export function ResultCards({
  response,
  platform = null,
  onSuggestedChip,
  onStrategyToAd,
  onSelectProposal,
  selectedProposalIndex = null,
  publishedProposalIndex = null,
}: ResultCardsProps) {
  const result = response.result ?? {};
  const title = typeof result.title === "string" ? result.title : "생성 결과";
  const proposals = Array.isArray(result.proposals) ? result.proposals : [];
  const strategy =
    typeof result.strategy === "object" && result.strategy !== null
      ? (result.strategy as { summary?: string; actions?: Array<{ type?: string; content?: string }> })
      : null;
  const reasons = Array.isArray(result.reasons) ? result.reasons.filter((item): item is string => typeof item === "string") : [];
  const sources = Array.isArray(result.sources) ? result.sources.filter((item): item is string => typeof item === "string") : [];
  const suggestedChips = Array.isArray(result.suggested_chips) ? result.suggested_chips.filter((item): item is string => typeof item === "string") : [];
  const isXBanner = platform === "xbanner";

  return (
    <section className={`result-section${isXBanner ? " result-section--xbanner" : ""}`}>
      <div className="section-heading">
        <div><p className="kicker">GENERATION #{response.generation_id}</p><h2>{title}</h2></div>
        <span className="plan-pill">{response.usage.plan} · {response.usage.credits_used} Credit</span>
      </div>
      {isXBanner && <p className="result-format-note" role="note">세로형 X-배너 · 상단 카피와 하단 가게 정보가 이어진 결과입니다.</p>}
      {response.chatbot_type === "basic" ? (
        <div className="proposal-grid">
          {Array.from({ length: 3 }, (_, index) => {
            const proposalIndex = index as ProposalIndex;
            const raw = proposals[index];
            const proposal = (raw ?? {}) as { copy?: string | null; image_b64?: string | null; error?: { message?: string } | null };
            const canSelect = typeof proposal.copy === "string" && proposal.copy.trim().length > 0;
            const imageSource = proposal.image_b64?.startsWith("data:")
              ? proposal.image_b64
              : proposal.image_b64
                ? `data:image/png;base64,${proposal.image_b64}`
                : null;
            const isPublished = publishedProposalIndex === proposalIndex;
            const isSelected = selectedProposalIndex === proposalIndex;
            const actionLabel = isPublished
              ? `제안 ${index + 1} 게시됨`
              : !canSelect
                ? "선택 불가"
                : isSelected
                  ? "선택됨"
                  : "이 제안 선택";
            const actionClass = isPublished ? " is-published" : isSelected ? " is-selected" : "";
            return (
              <article className={`card proposal${isXBanner ? " proposal--xbanner" : ""}${isPublished ? " proposal-published" : ""}${isSelected ? " proposal-selected" : ""}`} key={index}>
                <div className="proposal-visual">{imageSource ? <img className="proposal-image" src={imageSource} alt={`제안 ${index + 1} 이미지`} /> : <div className="proposal-image proposal-image-placeholder"><span>IMAGE</span><small>이미지 결과 영역</small></div>}</div>
                <div className="proposal-copy"><span>제안 {index + 1}</span><p>{proposal.copy ?? proposal.error?.message ?? "결과가 없습니다."}</p><button type="button" className={`proposal-action${actionClass}`} disabled={!canSelect || publishedProposalIndex !== null} aria-pressed={isSelected || isPublished} onClick={() => onSelectProposal?.(proposalIndex)}><span className="proposal-action-icon" aria-hidden="true">{isPublished ? "✓" : isSelected ? "✓" : canSelect ? "＋" : "–"}</span><span>{actionLabel}</span></button></div>
              </article>
            );
          })}
        </div>
      ) : (
        <article className="card strategy-card">
          <p className="strategy-summary">{strategy?.summary ?? "전략 요약이 없습니다."}</p>
          <div className="strategy-actions">{strategy?.actions?.map((action, index) => { const type = action.type ?? "other"; const meta = actionMeta[type] ?? actionMeta.other; return <article className={`strategy-action strategy-action-${type}`} key={index}><div className="strategy-action-icon" aria-hidden="true">{meta.visual}</div><div><span>{String(index + 1).padStart(2, "0")} · {meta.label}</span><p>{action.content}</p></div></article>; })}</div>
          {reasons.length > 0 && <details className="result-details"><summary>이렇게 제안한 이유 <span>{reasons.length}</span></summary><ul>{reasons.map((reason) => <li key={reason}>{reason}</li>)}</ul></details>}
          {sources.length > 0 && <details className="result-details"><summary>참고 근거 <span>{sources.length}</span></summary><ul>{sources.map((source) => <li key={source}>{source}</li>)}</ul></details>}
          {suggestedChips.length > 0 && <div className="suggested-chips">{suggestedChips.slice(0, 3).map((chip) => <button type="button" key={chip} onClick={() => onSuggestedChip?.(chip)}>{chip}</button>)}</div>}
          {onStrategyToAd && <button type="button" className="strategy-to-ad" onClick={() => onStrategyToAd(response.generation_id, strategy?.summary?.slice(0, 120) ?? "")}><span aria-hidden="true">✦</span><span><strong>이 전략으로 광고 만들기</strong><small>Basic 챗봇에서 플랫폼을 선택해 이어서 생성합니다.</small></span><span aria-hidden="true">→</span></button>}
        </article>
      )}
    </section>
  );
}
