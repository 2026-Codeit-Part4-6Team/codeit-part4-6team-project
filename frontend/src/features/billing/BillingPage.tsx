import { useEffect, useState } from "react";

import type { ApiClient, PaymentPackage } from "../../api";
import { createIdempotencyKey } from "../../requestId";

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
  const [packages, setPackages] = useState<PaymentPackage[]>([]);
  const [catalogStatus, setCatalogStatus] = useState<"loading" | "ready" | "error">("loading");
  const [buying, setBuying] = useState<PaymentPackage["id"] | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let active = true;
    setCatalogStatus("loading");
    setPackages([]);
    void api.paymentCatalog()
      .then((catalog) => {
        if (!active) return;
        setPackages(catalog.packages);
        setCatalogStatus("ready");
      })
      .catch(() => {
        if (!active) return;
        setPackages([]);
        setCatalogStatus("error");
      });
    return () => {
      active = false;
    };
  }, [api]);

  async function purchase(packageId: PaymentPackage["id"]) {
    setBuying(packageId);
    setMessage(null);
    setError(null);
    try {
      const result = await api.purchasePackage(packageId, createIdempotencyKey());
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
        <p className="payment-notice" role="note">⚠️ PG 연동 전 단계입니다. 지금은 실제 결제가 발생하지 않고 크레딧만 지급됩니다 — 시연·테스트 용도입니다.</p>
      </div>
      {error && <p className="form-error" role="alert">{error}</p>}
      {message && <p className="saved-note" role="status">{message}</p>}
      {catalogStatus === "loading" && <p role="status">가격 정보를 불러오는 중입니다.</p>}
      {catalogStatus === "error" && <p className="form-error" role="alert">가격 정보를 불러오지 못했습니다. 잠시 후 다시 시도해 주세요.</p>}
      <div className="billing-gate-grid" aria-busy={catalogStatus === "loading"}>
        {packages.map((item) => (
          <article className="card billing-gate-card" key={item.id}>
            <span>{item.discount_percent}% 할인</span>
            <h2>{item.id}</h2>
            <strong>{item.credits.toLocaleString("ko-KR")} 크레딧</strong>
            <p>{money(item.amount)} <small>VAT 별도</small></p>
            <button type="button" className="primary" disabled={buying !== null} onClick={() => void purchase(item.id)}>
              {buying === item.id ? "처리 중…" : "충전하기 (시연용)"}
            </button>
          </article>
        ))}
      </div>
    </section>
  );
}
