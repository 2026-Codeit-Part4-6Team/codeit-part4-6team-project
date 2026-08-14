import type { AppRoute } from "../appState";

type DashboardHomeProps = {
  onNavigate: (route: AppRoute) => void;
};

export function DashboardHome({ onNavigate }: DashboardHomeProps) {
  return (
    <section className="dashboard-home" aria-labelledby="dashboard-title">
      <div className="dashboard-greeting">
        <span className="greeting-mark" aria-hidden="true" />
        <h1 id="dashboard-title">안녕하세요, 사장님!</h1>
        <p>왼쪽 사이드바나 아래 카드에서 원하는 기능을 선택하세요.<br />AI가 마케팅을 도와드립니다.</p>
      </div>

      <div className="feature-card-grid">
        <button type="button" className="feature-card" onClick={() => onNavigate("consultant_chatbot")}>
          <img src="/assets/message-circle-large.svg" alt="" aria-hidden="true" />
          <strong>컨설턴트 챗봇</strong>
          <span>상권 분석 &amp; 전략 제안</span>
        </button>
        <button type="button" className="feature-card" onClick={() => onNavigate("basic_chatbot")}>
          <img src="/assets/file-text-large.svg" alt="" aria-hidden="true" />
          <strong>게시물 생성</strong>
          <span>SNS &amp; 현수막</span>
        </button>
      </div>
    </section>
  );
}
