import type { GenerationResponse } from "../../api";

export function ResultCards({ response }: { response: GenerationResponse }) {
  const result = response.result ?? {};
  const title = typeof result.title === "string" ? result.title : "생성 결과";
  const proposals = Array.isArray(result.proposals) ? result.proposals : [];
  const strategy =
    typeof result.strategy === "object" && result.strategy !== null
      ? (result.strategy as { summary?: string; actions?: Array<{ type?: string; content?: string }> })
      : null;

  return (
    <section className="result-section">
      <div className="section-heading">
        <div><p className="kicker">GENERATION #{response.generation_id}</p><h2>{title}</h2></div>
        <span className="plan-pill">{response.usage.plan} · {response.usage.credits_used} Credit</span>
      </div>
      {response.chatbot_type === "basic" ? (
        <div className="proposal-grid">
          {proposals.map((raw, index) => {
            const proposal = raw as { copy?: string | null; error?: { message?: string } | null };
            return (
              <article className="card proposal" key={index}>
                <span>제안 {index + 1}</span>
                <p>{proposal.copy ?? proposal.error?.message ?? "결과가 없습니다."}</p>
              </article>
            );
          })}
        </div>
      ) : (
        <article className="card strategy-card">
          <p>{strategy?.summary ?? "전략 요약이 없습니다."}</p>
          <ul>{strategy?.actions?.map((action, index) => <li key={index}><b>{action.type}</b> {action.content}</li>)}</ul>
        </article>
      )}
    </section>
  );
}
