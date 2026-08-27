const packages = ["starter", "standard", "pro"] as const;

export function BillingPage({ onBack }: { onBack: () => void }) {
  return (
    <section className="billing-page" aria-labelledby="billing-title">
      <button type="button" className="back-link" onClick={onBack}>← 대시보드로 돌아가기</button>
      <div className="page-heading">
        <p className="kicker">PAYMENT POLICY GATE</p>
        <h1 id="billing-title">결제 정책 확정 대기</h1>
        <p>가격과 지급량, 상태 전이, 중복 방지 기준을 팀 합의 후 제공합니다.</p>
      </div>
      <div className="billing-gate-grid">
        {packages.map((name) => (
          <article className="card billing-gate-card" key={name}>
            <span>PACKAGE ID</span>
            <h2>{name}</h2>
            <button type="button" disabled>정책 대기</button>
          </article>
        ))}
      </div>
    </section>
  );
}
