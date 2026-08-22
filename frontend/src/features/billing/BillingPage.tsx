import { useEffect, useState } from "react";

import type { ApiClient, PaymentPackage } from "../../api";

const fallbackPackages: PaymentPackage[] = [
  { id: "starter", credits: 5_000, amount: 48_500, discount_percent: 3 },
  { id: "standard", credits: 10_000, amount: 93_000, discount_percent: 7 },
  { id: "pro", credits: 20_000, amount: 180_000, discount_percent: 10 },
];

function money(amount: number) {
  return `${amount.toLocaleString("ko-KR")}원`;
}

export function BillingPage({
  api,
  currentCredits,
  onCreditsChanged,
  onBack,
}: {
  api: ApiClient;
  currentCredits: number;
  onCreditsChanged?: (credits: number) => void;
  onBack: () => void;
}) {
  const [packages, setPackages] = useState(fallbackPackages);
  const [buying, setBuying] = useState<PaymentPackage["id"] | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    void api.paymentCatalog().then((catalog) => setPackages(catalog.packages)).catch(() => undefined);
  }, [api]);

  async function purchase(packageId: PaymentPackage["id"]) {
    setBuying(packageId);
    setMessage(null);
    setError(null);
    try {
      const result = await api.purchasePackage(packageId, crypto.randomUUID());
      onCreditsChanged?.(result.balance);
      setMessage(`${result.credits.toLocaleString("ko-KR")} 크레딧이 충전되었습니다. 현재 잔액 ${result.balance.toLocaleString("ko-KR")} 크레딧`);
    } catch {
      setError("결제를 완료하지 못했습니다. 잠시 후 다시 시도해 주세요.");
    } finally {
      setBuying(null);
    }
  }

  return (
    <section className="billing-page" aria-labelledby="billing-title">
      <button type="button" className="back-link" onClick={onBack}>← 대시보드로 돌아가기</button>
      <div className="page-heading">
        <p className="kicker">CREDIT STORE</p>
        <h1 id="billing-title">크레딧 충전</h1>
        <p>현재 잔액 {currentCredits.toLocaleString("ko-KR")} 크레딧 · 모든 금액은 VAT 별도입니다.</p>
      </div>
      {error && <p className="form-error" role="alert">{error}</p>}
      {message && <p className="saved-note" role="status">{message}</p>}
      <div className="billing-gate-grid">
        {packages.map((item) => (
          <article className="card billing-gate-card" key={item.id}>
            <span>{item.discount_percent}% 할인</span>
            <h2>{item.id}</h2>
            <strong>{item.credits.toLocaleString("ko-KR")} 크레딧</strong>
            <p>{money(item.amount)} <small>VAT 별도</small></p>
            <button type="button" className="primary" disabled={buying !== null} onClick={() => void purchase(item.id)}>
              {buying === item.id ? "처리 중…" : "결제하기"}
            </button>
          </article>
        ))}
      </div>
    </section>
  );
}
