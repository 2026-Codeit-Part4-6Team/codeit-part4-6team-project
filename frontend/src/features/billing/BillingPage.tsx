import { useEffect, useState } from "react";

import {
  type ApiClient,
  type DemoPaymentCatalogResponse,
  type DemoPaymentPackage,
  type DemoPaymentResponse,
} from "../../api";
import { createIdempotencyKey } from "../../requestId";

const closedCatalog: DemoPaymentCatalogResponse = {
  demo_enabled: false,
  packages: [
    { id: "starter", amount: 0, credits: 0 },
    { id: "standard", amount: 0, credits: 0 },
    { id: "pro", amount: 0, credits: 0 },
  ],
};

type BillingPageProps = {
  onBack: () => void;
  api?: Pick<ApiClient, "paymentCatalog" | "purchaseDemoPackage">;
  currentCredits?: number;
  onCreditsChanged?: (credits: number) => void;
  demoCatalog?: DemoPaymentCatalogResponse;
};

function formatAmount(value: number): string {
  return `${value.toLocaleString("ko-KR")}원`;
}

export function BillingPage({
  onBack,
  api,
  currentCredits = 0,
  onCreditsChanged = () => undefined,
  demoCatalog,
}: BillingPageProps) {
  const [catalog, setCatalog] = useState(demoCatalog ?? closedCatalog);
  const [loading, setLoading] = useState(api !== undefined && demoCatalog === undefined);
  const [busyPackage, setBusyPackage] = useState<DemoPaymentPackage["id"] | null>(null);
  const [completed, setCompleted] = useState<DemoPaymentResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (api === undefined || demoCatalog !== undefined) return;
    let active = true;
    api.paymentCatalog()
      .then((next) => { if (active) setCatalog(next); })
      .catch(() => { if (active) setError("결제 데모 정보를 불러오지 못했습니다."); })
      .finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, [api, demoCatalog]);

  async function purchase(packageId: DemoPaymentPackage["id"]) {
    if (api === undefined || busyPackage !== null) return;
    setBusyPackage(packageId);
    setError(null);
    try {
      const response = await api.purchaseDemoPackage(packageId, createIdempotencyKey());
      setCompleted(response);
      onCreditsChanged(response.balance);
    } catch {
      setError("데모 충전에 실패했습니다. 다시 시도해 주세요.");
    } finally {
      setBusyPackage(null);
    }
  }

  if (!catalog.demo_enabled) {
    return (
      <section className="billing-page" aria-labelledby="billing-title">
        <button type="button" className="back-link" onClick={onBack}>← 대시보드로 돌아가기</button>
        <div className="page-heading">
          <p className="kicker">PAYMENT POLICY GATE</p>
          <h1 id="billing-title">결제 정책 확정 대기</h1>
          <p>{loading ? "결제 설정을 확인하고 있습니다." : "가격과 지급량, 상태 전이, 중복 방지 기준을 팀 합의 후 제공합니다."}</p>
        </div>
        {error && <div className="error-banner" role="alert">{error}</div>}
        <div className="billing-gate-grid">
          {closedCatalog.packages.map((item) => (
            <article className="card billing-gate-card" key={item.id}>
              <span>PACKAGE ID</span>
              <h2>{item.id}</h2>
              <button type="button" disabled>정책 대기</button>
            </article>
          ))}
        </div>
      </section>
    );
  }

  return (
    <section className="billing-page" aria-labelledby="billing-title">
      <button type="button" className="back-link" onClick={onBack}>← 대시보드로 돌아가기</button>
      <div className="page-heading billing-demo-heading">
        <p className="kicker">DEMO PAYMENT</p>
        <span className="demo-badge">시연용 결제</span>
        <h1 id="billing-title">발표용 Credit 충전</h1>
        <p>실제 결제가 발생하지 않는 데모입니다. 현재 잔액은 {currentCredits.toLocaleString("ko-KR")} Credit입니다.</p>
      </div>
      {completed && <div className="payment-success" role="status"><strong>{completed.credits.toLocaleString("ko-KR")} Credit 충전 완료</strong><span>새 잔액 {completed.balance.toLocaleString("ko-KR")} Credit</span></div>}
      {error && <div className="error-banner" role="alert">{error}</div>}
      <div className="billing-gate-grid billing-demo-grid">
        {catalog.packages.map((item) => (
          <article className="card billing-gate-card billing-demo-card" key={item.id}>
            <span>DEMO PACKAGE</span>
            <h2>{item.id}</h2>
            <strong>{formatAmount(item.amount)}</strong>
            <p>{item.credits.toLocaleString("ko-KR")} Credit</p>
            <button type="button" disabled={busyPackage !== null} onClick={() => void purchase(item.id)}>{busyPackage === item.id ? "처리 중…" : "데모 충전"}</button>
          </article>
        ))}
      </div>
    </section>
  );
}
