import type { AppRoute } from "../appState";

type DashboardHomeProps = {
  onNavigate: (route: AppRoute) => void;
};

export function DashboardHome({ onNavigate }: DashboardHomeProps) {
  return (
    <section className="dashboard-home" aria-labelledby="dashboard-title">
      <div className="mascot-hero">
        <div className="dashboard-greeting">
          <p className="kicker">YOUR AI GROWTH PARTNERS</p>
          <h1 id="dashboard-title">안녕하세요, 사장님!</h1>
          <p><strong>카피니와 분석이</strong>가 광고 제작부터 상권 전략까지 함께합니다.</p>
          <img
            className="hero-brand-logo"
            src="/assets/brand/salesbooster-logo.png"
            alt="매출부스터 AI"
          />
        </div>
        <div className="mascot-duo" aria-label="카피니와 분석이">
          <img className="mascot-duo-copyni" src="/assets/mascots/copyni.png" alt="광고 제작 파트너 카피니" />
          <img className="mascot-duo-bunseoki" src="/assets/mascots/bunseoki.png" alt="상권 분석 파트너 분석이" />
        </div>
      </div>

      <div className="feature-card-grid">
        <button type="button" className="feature-card feature-card-consultant" onClick={() => onNavigate("consultant_chatbot")}>
          <img className="feature-mascot" src="/assets/mascots/bunseoki.png" alt="" aria-hidden="true" />
          <small>분석이에게 상담받기</small>
          <strong>컨설턴트 챗봇</strong>
          <span>상권 분석 &amp; 전략 제안</span>
        </button>
        <button type="button" className="feature-card feature-card-basic" onClick={() => onNavigate("basic_chatbot")}>
          <img className="feature-mascot" src="/assets/mascots/copyni.png" alt="" aria-hidden="true" />
          <small>카피니와 광고 만들기</small>
          <strong>게시물 생성</strong>
          <span>SNS &amp; X-배너</span>
        </button>
      </div>
    </section>
  );
}
