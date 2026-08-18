import type { GenerationResponse } from "../../api";

const actionMeta: Record<string, { label: string; icon: string }> = {
  menu: { label: "메뉴 구성", icon: "✦" },
  promotion: { label: "프로모션", icon: "↗" },
  target: { label: "타깃 고객", icon: "◎" },
  other: { label: "추가 제안", icon: "＋" },
};

export function ResultCards({ response, onSuggestedChip }: { response: GenerationResponse; onSuggestedChip?: (chip: string) => void }) {
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

  return (
    <section className="result-section">
      <div className="section-heading">
        <div><p className="kicker">GENERATION #{response.generation_id}</p><h2>{title}</h2></div>
        <span className="plan-pill">{response.usage.plan} · {response.usage.credits_used} Credit</span>
      </div>
      {response.chatbot_type === "basic" ? (
        <div className="proposal-grid">
          {proposals.map((raw, index) => {
            const proposal = raw as { copy?: string | null; image_b64?: string | null; error?: { message?: string } | null };
            return (
              <article className="card proposal" key={index}>
                <div className="proposal-visual">{proposal.image_b64 ? <img className="proposal-image" src={`data:image/png;base64,${proposal.image_b64}`} alt={`제안 ${index + 1} 이미지`} /> : <div className="proposal-image proposal-image-placeholder"><span>IMAGE</span><small>이미지 결과 영역</small></div>}</div>
                <div className="proposal-copy"><span>제안 {index + 1}</span><p>{proposal.copy ?? proposal.error?.message ?? "결과가 없습니다."}</p><button type="button" className="proposal-action">이 제안 선택</button></div>
              </article>
            );
          })}
        </div>
      ) : (
        <article className="card strategy-card">
          <p className="strategy-summary">{strategy?.summary ?? "전략 요약이 없습니다."}</p>
          <div className="strategy-actions">{strategy?.actions?.map((action, index) => { const meta = actionMeta[action.type ?? "other"] ?? actionMeta.other; return <article className="strategy-action" key={index}><div className="strategy-action-icon">{meta.icon}</div><div><span>{String(index + 1).padStart(2, "0")} · {meta.label}</span><p>{action.content}</p></div></article>; })}</div>
          {reasons.length > 0 && <details className="result-details"><summary>이렇게 제안한 이유 <span>{reasons.length}</span></summary><ul>{reasons.map((reason) => <li key={reason}>{reason}</li>)}</ul></details>}
          {sources.length > 0 && <details className="result-details"><summary>참고 근거 <span>{sources.length}</span></summary><ul>{sources.map((source) => <li key={source}>{source}</li>)}</ul></details>}
          {suggestedChips.length > 0 && <div className="suggested-chips">{suggestedChips.slice(0, 3).map((chip) => <button type="button" key={chip} onClick={() => onSuggestedChip?.(chip)}>{chip}</button>)}</div>}
        </article>
      )}
    </section>
  );
}
