import type { AppRoute } from "./appState";
import type { ApiClient, UserResponse } from "./api";
import { DashboardHome } from "./components/DashboardHome";
import { DashboardLayout } from "./components/DashboardLayout";
import { GenerationLab } from "./features/generation/GenerationLab";
import { BillingPage } from "./features/billing/BillingPage";
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
    content = <GenerationLab key="basic-generation" api={api} chatbotType="basic" />;
  } else if (route === "consultant_chatbot") {
    content = <GenerationLab key="consultant-generation" api={api} chatbotType="consultant" />;
  } else if (route === "mypage") {
    content = <MyPage api={api} user={user} onBack={() => onNavigate("dashboard")} onBilling={() => onNavigate("billing")} />;
  } else if (route === "settings") {
    content = <SettingsPage onBack={() => onNavigate("dashboard")} />;
  } else {
    content = <BillingPage onBack={() => onNavigate("dashboard")} />;
  }

  return (
    <DashboardLayout user={user} route={route} onNavigate={onNavigate} onLogout={onLogout}>
      {content}
    </DashboardLayout>
  );
}
