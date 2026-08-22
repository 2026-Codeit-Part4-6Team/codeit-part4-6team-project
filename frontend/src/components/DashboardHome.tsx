import type { AppRoute } from "../appState";

type DashboardHomeProps = {
  onNavigate: (route: AppRoute) => void;
};

export function DashboardHome({ onNavigate }: DashboardHomeProps) {
  return (
    <section className="dashboard-home" aria-labelledby="dashboard-title">
      <div className="mascot-hero mascot-hero--compact dashboard-hero--text-only">
        <div className="dashboard-greeting">
          <p className="kicker dashboard-kicker">AI 성장 파트너</p>
          <h1 id="dashboard-title" className="dashboard-greeting-title">안녕하세요, 사장님!</h1>
          <p className="dashboard-greeting-copy"><strong>카피니와 분석이</strong>가 광고 제작부터 상권 전략까지 함께합니다.</p>
        </div>
      </div>

      <div className="feature-card-grid">
        <button type="button" className="feature-card feature-card--visual feature-card-consultant" onClick={() => onNavigate("consultant_chatbot")}>
          <img className="feature-mascot" src="/assets/mascots/bunseoki.png" alt="" aria-hidden="true" />
          <small>분석이에게 상담받기</small>
          <strong>컨설턴트 챗봇</strong>
          <span>상권 분석 &amp; 전략 제안</span>
          <span className="feature-card-cta" aria-hidden="true">상담 시작하기 →</span>
        </button>
        <button type="button" className="feature-card feature-card--visual feature-card-basic" onClick={() => onNavigate("basic_chatbot")}>
          <img className="feature-mascot" src="/assets/mascots/copyni.png" alt="" aria-hidden="true" />
          <small>카피니와 광고 만들기</small>
          <strong>게시물 생성</strong>
          <span>SNS &amp; X-배너</span>
          <span className="feature-card-cta" aria-hidden="true">광고 만들기 →</span>
        </button>
      </div>
    </section>
  );
}
