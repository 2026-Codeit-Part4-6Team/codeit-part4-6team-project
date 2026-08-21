import { useState } from "react";

import { ApiError, type ApiClient, type UserResponse } from "../api";

type ModelId = "service_basic" | "service_advanced" | "pending";

const models: Array<{ id: ModelId; name: string; detail: string }> = [
  { id: "service_basic", name: "기본 제공 모델", detail: "서비스에서 제공하는 기본 생성 모델" },
  { id: "service_advanced", name: "고급 제공 모델", detail: "서비스에서 제공하는 고급 생성 모델" },
  { id: "pending", name: "모델 설정 준비 중", detail: "제공 모델 확정 후 선택 항목을 갱신합니다" },
];

// 제공 Provider가 확정되기 전까지는 실제 업체명을 UI 계약으로 고정하지 않는다.

type SettingsPageProps = {
  api: ApiClient;
  user: UserResponse;
  onBack: () => void;
  onUserChanged?: (user: UserResponse) => void;
};

export function SettingsPage({ api, user, onBack, onUserChanged }: SettingsPageProps) {
  const [modelType, setModelType] = useState<ModelId>("service_basic");
  const [saved, setSaved] = useState(false);
  const [credits, setCredits] = useState(user.credits);
  const [dailyFreeUsed, setDailyFreeUsed] = useState(user.daily_free_used);
  const [demoBusy, setDemoBusy] = useState(false);
  const [demoMessage, setDemoMessage] = useState<string | null>(null);

  function changeModel(value: ModelId) {
    setModelType(value);
    setSaved(false);
  }


  async function applyDemoState() {
    setDemoBusy(true);
    setDemoMessage(null);
    try {
      const updated = await api.updateDemoTestState({
        credits,
        daily_free_used: dailyFreeUsed,
      });
      onUserChanged?.(updated);
      setDemoMessage("데모 계정 상태를 반영했습니다.");
    } catch (error) {
      setDemoMessage(
        error instanceof ApiError && error.statusCode === 422
          ? "무료 사용량은 일일 한도 안에서 입력해 주세요."
          : "데모 계정 상태를 변경하지 못했습니다.",
      );
    } finally {
      setDemoBusy(false);
    }
  }

  return (
    <section className="account-page settings-page" aria-labelledby="settings-title">
      <button type="button" className="back-link" onClick={onBack}>← 대시보드로 돌아가기</button>
      <div className="page-heading"><p className="kicker">SETTINGS</p><h1 id="settings-title">환경설정</h1><p>서비스를 사용하는 기본 방식을 정리해두는 곳입니다.</p></div>
      <div className="settings-stack">
        <section className="card settings-card settings-model-card">
          <div><p className="kicker">AI PROVIDER</p><h2>사용할 AI 모델</h2><p>광고 생성과 후속 대화에 사용할 모델을 선택하세요.</p></div>
          <div className="model-options">
            {models.map((model) => <button type="button" aria-pressed={modelType === model.id} className={modelType === model.id ? "selected" : ""} onClick={() => changeModel(model.id)} key={model.id}><span>{model.id === "service_basic" ? "◈" : model.id === "service_advanced" ? "✦" : "✺"}</span><strong>{model.name}</strong><small>{model.detail}</small></button>)}
          </div>
          {saved && <p className="saved-note">환경설정 미리보기에 반영했습니다.</p>}
          <button type="button" className="primary settings-save" onClick={() => setSaved(true)}>설정 저장</button>
        </section>
        {user.is_admin && (
          <section className="card settings-card demo-test-card">
            <div>
              <p className="kicker">DEMO ONLY</p>
              <h2>데모 계정 상태</h2>
              <p>시연할 과금 흐름에 맞춰 이 관리자 계정의 상태만 조절합니다.</p>
            </div>
            <div className="demo-test-fields">
              <label>
                <span>현재 크레딧</span>
                <input
                  type="number"
                  min="0"
                  value={credits}
                  onChange={(event) => setCredits(Number(event.target.value))}
                />
              </label>
              <label>
                <span>오늘 무료 사용량</span>
                <input
                  type="number"
                  min="0"
                  max={user.daily_free_used + user.daily_free_remaining}
                  value={dailyFreeUsed}
                  onChange={(event) => setDailyFreeUsed(Number(event.target.value))}
                />
              </label>
            </div>
            {demoMessage && <p className="saved-note" role="status">{demoMessage}</p>}
            <button
              type="button"
              className="primary settings-save"
              disabled={demoBusy}
              onClick={() => void applyDemoState()}
            >
              {demoBusy ? "반영 중…" : "테스트 상태 적용"}
            </button>
          </section>
        )}
        <section className="card settings-card muted-settings"><p className="kicker">MORE LATER</p><h2>추가 설정</h2><p>팀 의견을 받은 뒤 필요한 설정을 이 영역에 추가합니다.</p></section>
      </div>
    </section>
  );
}
