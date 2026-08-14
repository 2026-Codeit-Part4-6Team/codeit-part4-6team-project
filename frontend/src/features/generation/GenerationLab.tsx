import { type FormEvent, useState } from "react";

import { ApiError, type ApiClient, type GenerationResponse } from "../../api";
import {
  buildEstimatePayload,
  type ChatbotType,
  type EstimateResponse,
  type Platform,
} from "../../contract";
import {
  apiErrorMessage,
  createPendingGeneration,
  generationPayload,
  type PendingGeneration,
} from "../../state";
import { ResultCards } from "./ResultCards";

function messageFrom(error: unknown): string {
  if (error instanceof ApiError) return apiErrorMessage(error.statusCode, error.detail);
  return "Backend에 연결할 수 없습니다.";
}

function EstimateCard({ estimate, busy, onGenerate }: { estimate: EstimateResponse; busy: boolean; onGenerate: () => void }) {
  return (
    <section className="card estimate-card">
      <div>
        <p className="kicker">ESTIMATE</p>
        <h3>{estimate.requires_confirmation ? `${estimate.estimated_credits} Credit 사용` : "무료 생성 가능"}</h3>
        <p>현재 {estimate.current_credits ?? 0} → 생성 후 {estimate.credits_after ?? 0} Credit</p>
      </div>
      <button type="button" className="primary" onClick={onGenerate} disabled={busy}>
        {busy ? "생성 중…" : "이 조건으로 생성"}
      </button>
    </section>
  );
}

export function GenerationLab({ api }: { api: ApiClient }) {
  const [chatbotType, setChatbotType] = useState<ChatbotType>("basic");
  const [platform, setPlatform] = useState<Platform>("instagram");
  const [question, setQuestion] = useState("");
  const [pending, setPending] = useState<PendingGeneration | null>(null);
  const [generation, setGeneration] = useState<GenerationResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function estimate(event: FormEvent) {
    event.preventDefault();
    if (busy) return;
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
    if (!pending || busy) return;
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
    <section className="generation-page" aria-labelledby="generation-title">
      <div className="generation-heading">
        <p className="kicker">CONNECTED GENERATION POC</p>
        <h1 id="generation-title">게시물 생성</h1>
        <p>기존 Estimate·Generate 연결을 유지했습니다. 내부 화면의 Figma 재설계는 다음 단계에서 진행합니다.</p>
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
              <option value="banner">현수막</option>
            </select>
          </label>
        )}
        <label>무엇을 만들까요?
          <textarea
            value={question}
            onChange={(event) => setQuestion(event.target.value)}
            maxLength={2000}
            required
            placeholder="예: 여름 신메뉴를 알리는 활기찬 광고를 만들어줘"
          />
        </label>
        <button className="primary" disabled={busy}>{busy ? "확인 중…" : "예상 사용량 확인"}</button>
      </form>

      {error && <div className="error-banner wide" role="alert">{error}</div>}
      {pending && <EstimateCard estimate={pending.estimate} busy={busy} onGenerate={generate} />}
      {generation && <ResultCards response={generation} />}
    </section>
  );
}
