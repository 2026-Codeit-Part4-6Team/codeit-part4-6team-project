import type { UserResponse } from "../api";

const history = [
  { title: "여름 신메뉴 홍보", type: "Basic 광고", status: "완료", date: "오늘" },
  { title: "강남 상권 분석", type: "Consultant", status: "완료", date: "어제" },
  { title: "주말 이벤트 문구", type: "Basic 광고", status: "게시됨", date: "8월 12일" },
];

export function MyPage({ user, onBack }: { user: UserResponse; onBack: () => void }) {
  return (
    <section className="account-page" aria-labelledby="mypage-title">
      <button type="button" className="back-link" onClick={onBack}>← 대시보드로 돌아가기</button>
      <div className="page-heading">
        <p className="kicker">MY PAGE</p>
        <h1 id="mypage-title">내 활동을 한눈에 확인하세요.</h1>
        <p>{user.business_name ?? user.username}님의 생성 기록과 사용 현황입니다.</p>
      </div>
      <div className="summary-grid">
        <div className="stat-card"><span>현재 Credit</span><strong>{user.credits}</strong></div>
        <div className="stat-card"><span>오늘 무료 생성</span><strong>{user.daily_free_remaining}</strong></div>
        <div className="stat-card"><span>전체 생성</span><strong>12</strong></div>
        <div className="stat-card"><span>게시 완료</span><strong>4</strong></div>
      </div>
      <section className="card history-card">
        <div className="section-heading"><div><p className="kicker">RECENT ACTIVITY</p><h2>최근 생성 기록</h2></div><span className="muted">스토리보드 데이터</span></div>
        <div className="history-list">{history.map((item) => <div className="history-row" key={item.title}><div><strong>{item.title}</strong><span>{item.type}</span></div><div><span className="status-chip">{item.status}</span><small>{item.date}</small></div></div>)}</div>
      </section>
    </section>
  );
}
