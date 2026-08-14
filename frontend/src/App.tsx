import { type FormEvent, useEffect, useMemo, useState } from "react";

import { ApiClient, ApiError, type GenerationResponse, type UserResponse } from "./api";
import {
  buildEstimatePayload,
  type ChatbotType,
  type EstimateResponse,
  type Platform,
} from "./contract";
import {
  apiErrorMessage,
  createPendingGeneration,
  generationPayload,
  type PendingGeneration,
} from "./state";

function messageFrom(error: unknown): string {
  if (error instanceof ApiError) {
    return apiErrorMessage(error.statusCode, error.detail);
  }
  return "Backend에 연결할 수 없습니다.";
}

function Login({ api, onLogin }: { api: ApiClient; onLogin: (user: UserResponse) => void }) {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function submit(event: FormEvent) {
    event.preventDefault();
    setBusy(true);
    setError(null);
    try {
      onLogin(await api.login({ username, password }));
      setPassword("");
    } catch (caught) {
      setError(messageFrom(caught));
    } finally {
      setBusy(false);
    }
  }

  return (
    <main className="login-shell">
      <section className="login-copy">
        <p className="kicker">FIRST GENERATION POC</p>
        <h1>동네 가게의 이야기를<br />광고로 바꿉니다.</h1>
        <p>실제 Session Cookie와 생성 계약을 검증하는 React 실험입니다.</p>
      </section>
      <form className="card login-card" onSubmit={submit}>
        <div>
          <span className="brand-mark">⚡</span>
          <h2>매출부스터 로그인</h2>
        </div>
        <label>
          사용자명
          <input value={username} onChange={(event) => setUsername(event.target.value)} required />
        </label>
        <label>
          비밀번호
          <input
            type="password"
            value={password}
            onChange={(event) => setPassword(event.target.value)}
            minLength={8}
            required
          />
        </label>
        {error && <div className="error-banner">{error}</div>}
        <button className="primary" disabled={busy}>{busy ? "확인 중…" : "로그인"}</button>
      </form>
    </main>
  );
}

function ResultCards({ response }: { response: GenerationResponse }) {
  const result = response.result ?? {};
  const title = typeof result.title === "string" ? result.title : "생성 결과";
  const proposals = Array.isArray(result.proposals) ? result.proposals : [];
  const strategy =
    typeof result.strategy === "object" && result.strategy !== null
      ? (result.strategy as { summary?: string; actions?: Array<{ type?: string; content?: string }> })
      : null;

  return (
    <section className="result-section">
      <div className="section-heading">
        <div><p className="kicker">GENERATION #{response.generation_id}</p><h2>{title}</h2></div>
        <span className="plan-pill">{response.usage.plan} · {response.usage.credits_used} Credit</span>
      </div>
      {response.chatbot_type === "basic" ? (
        <div className="proposal-grid">
          {proposals.map((raw, index) => {
            const proposal = raw as { copy?: string | null; error?: { message?: string } | null };
            return (
              <article className="card proposal" key={index}>
                <span>제안 {index + 1}</span>
                <p>{proposal.copy ?? proposal.error?.message ?? "결과가 없습니다."}</p>
              </article>
            );
          })}
        </div>
      ) : (
        <article className="card strategy-card">
          <p>{strategy?.summary ?? "전략 요약이 없습니다."}</p>
          <ul>{strategy?.actions?.map((action, index) => <li key={index}><b>{action.type}</b> {action.content}</li>)}</ul>
        </article>
      )}
    </section>
  );
}

function GenerationLab({ api, user }: { api: ApiClient; user: UserResponse }) {
  const [chatbotType, setChatbotType] = useState<ChatbotType>("basic");
  const [platform, setPlatform] = useState<Platform>("instagram");
  const [question, setQuestion] = useState("");
  const [pending, setPending] = useState<PendingGeneration | null>(null);
  const [generation, setGeneration] = useState<GenerationResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function estimate(event: FormEvent) {
    event.preventDefault();
    setBusy(true);
    setError(null);
    try {
      const payload = buildEstimatePayload(chatbotType, question, platform);
      const response = await api.estimate(payload);
      setPending(createPendingGeneration(payload, response, crypto.randomUUID()));
      setGeneration(null);
    } catch (caught) {
      setError(messageFrom(caught));
    } finally {
      setBusy(false);
    }
  }

  async function generate() {
    if (!pending) return;
    setBusy(true);
    setError(null);
    try {
      setGeneration(await api.generate(generationPayload(pending), pending.idempotencyKey));
    } catch (caught) {
      setError(messageFrom(caught));
    } finally {
      setBusy(false);
    }
  }

  return (
    <main className="app-shell">
      <header>
        <div><p className="kicker">GENERATION LAB</p><h1>{user.business_name ?? user.username}</h1></div>
        <div className="account-badges">
          <span>{user.credits ?? 0} Credit</span>
          <span>무료 {user.daily_free_remaining ?? 0}회</span>
        </div>
      </header>

      <section className="hero-grid">
        <div className="hero-copy">
          <span className="brand-mark">⚡</span>
          <h2>오늘의 아이디어를<br />첫 광고로 만들어보세요.</h2>
          <p>Estimate를 먼저 확인한 뒤 같은 요청 키로 안전하게 생성합니다.</p>
        </div>
        <form className="card generation-card" onSubmit={estimate}>
          <div className="type-switch" role="group" aria-label="챗봇 유형">
            <button type="button" className={chatbotType === "basic" ? "active" : ""} onClick={() => setChatbotType("basic")}>광고 만들기</button>
            <button type="button" className={chatbotType === "consultant" ? "active" : ""} onClick={() => setChatbotType("consultant")}>상권 컨설팅</button>
          </div>
          {chatbotType === "basic" && (
            <label>광고 형식
              <select value={platform} onChange={(event) => setPlatform(event.target.value as Platform)}>
                <option value="instagram">Instagram</option>
                <option value="banner">배너</option>
              </select>
            </label>
          )}
          <label>무엇을 만들까요?
            <textarea value={question} onChange={(event) => setQuestion(event.target.value)} maxLength={2000} required placeholder="예: 여름 신메뉴를 알리는 활기찬 광고를 만들어줘" />
          </label>
          <button className="primary" disabled={busy}>{busy ? "확인 중…" : "예상 사용량 확인"}</button>
        </form>
      </section>

      {error && <div className="error-banner wide">{error}</div>}
      {pending && <EstimateCard estimate={pending.estimate} busy={busy} onGenerate={generate} />}
      {generation && <ResultCards response={generation} />}
    </main>
  );
}

function EstimateCard({ estimate, busy, onGenerate }: { estimate: EstimateResponse; busy: boolean; onGenerate: () => void }) {
  return (
    <section className="card estimate-card">
      <div>
        <p className="kicker">ESTIMATE</p>
        <h3>{estimate.requires_confirmation ? `${estimate.estimated_credits} Credit 사용` : "무료 생성 가능"}</h3>
        <p>현재 {estimate.current_credits ?? 0} → 생성 후 {estimate.credits_after ?? 0} Credit</p>
      </div>
      <button className="primary" onClick={onGenerate} disabled={busy}>{busy ? "생성 중…" : "이 조건으로 생성"}</button>
    </section>
  );
}

export function App() {
  const api = useMemo(() => new ApiClient(), []);
  const [user, setUser] = useState<UserResponse | null>(null);
  const [authChecked, setAuthChecked] = useState(false);

  useEffect(() => {
    api.me()
      .then(setUser)
      .catch((error) => {
        if (!(error instanceof ApiError && error.statusCode === 401)) console.error(error);
      })
      .finally(() => setAuthChecked(true));
  }, [api]);

  if (!authChecked) return <main className="loading">세션 확인 중…</main>;
  if (!user) return <Login api={api} onLogin={setUser} />;
  return <GenerationLab api={api} user={user} />;
}
