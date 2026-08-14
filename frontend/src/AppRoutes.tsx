import type { AppRoute } from "./appState";
import type { ApiClient, UserResponse } from "./api";
import { DashboardHome } from "./components/DashboardHome";
import { DashboardLayout } from "./components/DashboardLayout";
import { PlaceholderPage } from "./components/PlaceholderPage";
import { GenerationLab } from "./features/generation/GenerationLab";

type ProtectedRouteViewProps = {
  api: ApiClient;
  user: UserResponse;
  route: AppRoute;
  onNavigate: (route: AppRoute) => void;
  onLogout: () => void;
};

export function ProtectedRouteView({ api, user, route, onNavigate, onLogout }: ProtectedRouteViewProps) {
  let content;
  if (route === "dashboard") {
    content = <DashboardHome onNavigate={onNavigate} />;
  } else if (route === "basic_chatbot") {
    content = <GenerationLab api={api} />;
  } else if (route === "consultant_chatbot") {
    content = (
      <PlaceholderPage
        title="컨설턴트 챗봇"
        description="화면 진입 경로가 준비되었습니다. 실제 상담 기능은 다음 구현 단계에서 연결됩니다."
        onBack={() => onNavigate("dashboard")}
      />
    );
  } else if (route === "mypage") {
    content = (
      <PlaceholderPage
        title="마이페이지"
        description="마이페이지는 D9 범위입니다. 현재는 대시보드에서 계정 요약을 확인할 수 있습니다."
        onBack={() => onNavigate("dashboard")}
      />
    );
  } else {
    content = (
      <PlaceholderPage
        title="크레딧 충전"
        description="결제 정책이 확정되는 D9에서 안전한 충전 흐름을 연결합니다."
        onBack={() => onNavigate("dashboard")}
      />
    );
  }

  return (
    <DashboardLayout user={user} route={route} onNavigate={onNavigate} onLogout={onLogout}>
      {content}
    </DashboardLayout>
  );
}
