import { useCallback, useEffect, useMemo, useState } from "react";

import {
  authenticatedState,
  loggedOutState,
  navigate,
  startBasicFromStrategy,
  type AppRoute,
  type AppViewState,
} from "./appState";
import { ApiClient, ApiError, type UserResponse } from "./api";
import { ProtectedRouteView } from "./AppRoutes";
import { AuthScreen } from "./components/AuthScreen";

export function App() {
  const api = useMemo(() => new ApiClient(), []);
  const [view, setView] = useState<AppViewState>(loggedOutState);
  const [authChecked, setAuthChecked] = useState(false);
  const [restoreError, setRestoreError] = useState<string | null>(null);

  const restoreSession = useCallback(async () => {
    setRestoreError(null);
    try {
      setView(authenticatedState(await api.me()));
      setAuthChecked(true);
    } catch (error) {
      if (error instanceof ApiError && error.statusCode === 401) {
        setView(loggedOutState());
        setAuthChecked(true);
        return;
      }
      setRestoreError("로그인 상태를 확인하지 못했습니다. 잠시 후 다시 시도해 주세요.");
    }
  }, [api]);

  useEffect(() => {
    void restoreSession();
  }, [restoreSession]);

  function onAuthenticated(user: UserResponse) {
    setView(authenticatedState(user));
    setAuthChecked(true);
  }

  function onNavigate(route: AppRoute) {
    setView((current) => navigate(current, route));
  }

  function onStrategyToAd(sourceGenId: number, purpose: string) {
    setView((current) => startBasicFromStrategy(current, sourceGenId, purpose));
  }

  async function logout() {
    try {
      await api.logout();
    } finally {
      setView(loggedOutState());
      setAuthChecked(true);
    }
  }

  function updateCredits(credits: number) {
    setView((current) => current.user
      ? { ...current, user: { ...current.user, credits } }
      : current);
  }

  function onUserChanged(user: UserResponse) {
    setView((current) => ({ ...current, user }));
  }

  if (restoreError) {
    return (
      <main className="loading loading--error">
        <p>{restoreError}</p>
        <button type="button" className="primary" onClick={() => void restoreSession()}>다시 시도</button>
      </main>
    );
  }
  if (!authChecked) return <main className="loading">세션 확인 중…</main>;
  if (!view.user) return <AuthScreen api={api} onAuthenticated={onAuthenticated} />;
  return (
    <ProtectedRouteView
      api={api}
      user={view.user}
      route={view.route}
      generationPrefill={view.generationPrefill}
      onNavigate={onNavigate}
      onStrategyToAd={onStrategyToAd}
      onLogout={() => void logout()}
      onCreditsChanged={updateCredits}
      onUserChanged={onUserChanged}
    />
  );
}
