import type { AppRoute } from "./appState";
import type { ApiClient, UserResponse } from "./api";
import { DashboardHome } from "./components/DashboardHome";
import { DashboardLayout } from "./components/DashboardLayout";
import { PlaceholderPage } from "./components/PlaceholderPage";
import { GenerationLab } from "./features/generation/GenerationLab";
import { MyPage } from "./components/MyPage";
import { SettingsPage } from "./components/SettingsPage";

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
    content = <GenerationLab api={api} chatbotType="consultant" />;
  } else if (route === "mypage") {
    content = <MyPage user={user} onBack={() => onNavigate("dashboard")} />;
  } else if (route === "settings") {
    content = <SettingsPage onBack={() => onNavigate("dashboard")} />;
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
