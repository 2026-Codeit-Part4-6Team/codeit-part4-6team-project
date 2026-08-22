import type { AppRoute } from "../appState";
import type { UserResponse } from "../api";
import { BrandMark } from "./BrandMark";

type SidebarProps = {
  user: UserResponse;
  route: AppRoute;
  open: boolean;
  collapsed: boolean;
  onClose: () => void;
  onToggle: () => void;
  onNavigate: (route: AppRoute) => void;
  onLogout: () => void;
};

type NavigationItem = {
  route: AppRoute;
  label: string;
  icon: string;
};

const featureItems: NavigationItem[] = [
  { route: "consultant_chatbot", label: "컨설턴트 챗봇", icon: "/assets/message-circle.svg" },
  { route: "basic_chatbot", label: "게시물 생성", icon: "/assets/file-text.svg" },
];

function storeAddress(user: UserResponse): string {
  const base = user.road_address ?? user.address;
  return [base, user.address_detail].filter(Boolean).join(" ") || "주소 미등록";
}

function NavigationButton({
  item,
  currentRoute,
  onSelect,
}: {
  item: NavigationItem;
  currentRoute: AppRoute;
  onSelect: (route: AppRoute) => void;
}) {
  const current = item.route === currentRoute;
  return (
    <button
      type="button"
      className={`sidebar-nav-item${current ? " is-current" : ""}`}
      aria-current={current ? "page" : undefined}
      onClick={() => onSelect(item.route)}
    >
      <img src={item.icon} alt="" aria-hidden="true" />
      <span>{item.label}</span>
    </button>
  );
}

export function Sidebar({ user, route, open, collapsed, onClose, onNavigate, onLogout, onToggle }: SidebarProps) {
  const totalDaily = user.daily_free_used + user.daily_free_remaining;
  const dailyMax = Math.max(totalDaily, 1);

  function selectRoute(nextRoute: AppRoute) {
    onNavigate(nextRoute);
    onClose();
  }

  return (
    <aside id="app-sidebar" className={`sidebar${open ? " is-open" : ""}${collapsed ? " is-collapsed" : ""}`}>
      <div className="sidebar-brand">
        <BrandMark />
        <button type="button" className="sidebar-collapse" aria-label={collapsed ? "사이드바 펼치기" : "사이드바 접기"} aria-pressed={collapsed} onClick={onToggle}>{collapsed ? "»" : "«"}</button>
        <button type="button" className="sidebar-close" onClick={onClose} aria-label="메뉴 닫기">×</button>
      </div>

      <button type="button" className="store-card" onClick={() => selectRoute("dashboard")}>
        <span className="store-card-label"><img src="/assets/home.svg" alt="" /> 내 가게</span>
        <strong>{user.business_name ?? user.username}</strong>
        {user.is_admin === true && <span className="admin-badge">관리자 계정</span>}
        <span className="store-address"><img src="/assets/map-pin.svg" alt="" /> {storeAddress(user)}</span>
      </button>

      <section className="sidebar-section usage-section" aria-labelledby="usage-title">
        <h2 id="usage-title"><img src="/assets/usage.svg" alt="" /> 오늘 무료 사용량</h2>
        <progress value={user.daily_free_used} max={dailyMax}>
          {user.daily_free_used}/{dailyMax}
        </progress>
        <div className="usage-meta"><span>{user.daily_free_remaining}회 남음</span><span>매일 자정 초기화</span></div>
      </section>

      <section className="sidebar-section credit-section" aria-labelledby="credit-title">
        <div className="credit-heading">
          <h2 id="credit-title"><img src="/assets/credit.svg" alt="" /> 크레딧 잔액</h2>
          <button type="button" onClick={() => selectRoute("billing")}>+ 충전</button>
        </div>
        <p><strong>{user.credits}</strong> <span>크레딧</span></p>
      </section>

      <nav className="sidebar-navigation" aria-label="주요 기능">
        {featureItems.map((item) => (
          <NavigationButton key={item.route} item={item} currentRoute={route} onSelect={selectRoute} />
        ))}
      </nav>

      <nav className="sidebar-footer" aria-label="계정 기능">
        <NavigationButton
          item={{ route: "mypage", label: "마이페이지", icon: "/assets/history.svg" }}
          currentRoute={route}
          onSelect={selectRoute}
        />
        <NavigationButton
          item={{ route: "settings", label: "환경설정", icon: "/assets/settings.svg" }}
          currentRoute={route}
          onSelect={selectRoute}
        />
        <button type="button" className="sidebar-nav-item" onClick={onLogout}>
          <img src="/assets/logout.svg" alt="" aria-hidden="true" />
          <span>로그아웃</span>
        </button>
      </nav>
    </aside>
  );
}
