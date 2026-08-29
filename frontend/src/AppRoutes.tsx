import type { AppRoute, GenerationPrefill } from "./appState";
import type { ApiClient, UserResponse } from "./api";
import { DashboardHome } from "./components/DashboardHome";
import { DashboardLayout } from "./components/DashboardLayout";
import { GenerationLab } from "./features/generation/GenerationLab";
import { BillingPage } from "./features/billing/BillingPage";
import { MyPage } from "./components/MyPage";
import { SettingsPage } from "./components/SettingsPage";
import { StoreProfilePage } from "./components/StoreProfilePage";

type ProtectedRouteViewProps = {
  api: ApiClient;
  user: UserResponse;
  route: AppRoute;
  onNavigate: (route: AppRoute) => void;
  generationPrefill?: GenerationPrefill;
  onStrategyToAd?: (sourceGenId: number, strategySummary: string) => void;
  onLogout: () => void;
  onCreditsChanged?: (credits: number) => void;
  onUserChanged?: (user: UserResponse) => void;
};

export function ProtectedRouteView({ api, user, route, onNavigate, onStrategyToAd, onLogout, onCreditsChanged, onUserChanged, generationPrefill }: ProtectedRouteViewProps) {
  let content;
  if (route === "dashboard") {
    content = <DashboardHome onNavigate={onNavigate} />;
  } else if (route === "basic_chatbot") {
    content = <GenerationLab
      key="basic-generation"
      api={api}
      chatbotType="basic"
      initialQuestion={generationPrefill?.question}
      initialStrategySummary={generationPrefill?.strategy_summary}
      initialSourceGenId={generationPrefill?.source_gen_id}
      onUserChanged={onUserChanged}
    />;
  } else if (route === "consultant_chatbot") {
    content = <GenerationLab
      key="consultant-generation"
      api={api}
      chatbotType="consultant"
      onStrategyToAd={onStrategyToAd}
      onUserChanged={onUserChanged}
    />;
  } else if (route === "mypage") {
    content = <MyPage api={api} user={user} onBack={() => onNavigate("dashboard")} onBilling={() => onNavigate("billing")} />;
  } else if (route === "settings") {
    content = <SettingsPage onBack={() => onNavigate("dashboard")} />;
  } else if (route === "store_settings") {
    content = <StoreProfilePage api={api} user={user} onBack={() => onNavigate("dashboard")} onSaved={onUserChanged} />;
  } else {
    content = <BillingPage api={api} currentCredits={user.credits} onCreditsChanged={onCreditsChanged} onBack={() => onNavigate("dashboard")} />;
  }

  return (
    <DashboardLayout user={user} route={route} onNavigate={onNavigate} onLogout={onLogout}>
      {content}
    </DashboardLayout>
  );
}
