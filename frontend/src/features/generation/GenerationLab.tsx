import { type FormEvent, useEffect, useMemo, useState } from "react";

import { ApiError, type ApiClient, type GenerationResponse, type UserResponse } from "../../api";
import {
  buildEstimatePayload,
  type ChatbotType,
  type EstimateResponse,
  type GenerateExtra,
  type Platform,
} from "../../contract";
import {
  apiErrorMessage,
  createFollowUpMessage,
  generationPayload,
  nextGenerationAction,
  withClarification,
  type GenerationAction,
  type FollowUpMessage,
  type PendingGeneration,
} from "../../state";
import { CreditDialog } from "./CreditDialog";
import { isSuccessfulGeneration, ResultView } from "./ResultView";
import type { ProposalIndex } from "./ResultCards";
import { WaitingScreen } from "./WaitingScreen";

function messageFrom(error: unknown): string {
  if (error instanceof ApiError) return apiErrorMessage(error.statusCode, error.detail);
  return "Backend에 연결할 수 없습니다.";
}

type GenerationRunner = {
  run: (pending: PendingGeneration) => Promise<GenerationResponse>;
  dispose: () => void;
};

export async function syncUserAfterGeneration(
  api: Pick<ApiClient, "me">,
  onUserChanged?: (user: UserResponse) => void,
): Promise<void> {
  if (!onUserChanged) return;
  try {
    onUserChanged(await api.me());
  } catch {
    // 생성 결과는 성공했으므로 사용자 정보 갱신 실패가 결과를 가리면 안 됩니다.
  }
}

export function createGenerationRunner(
  api: Pick<ApiClient, "generate" | "waitingCopy">,
  onWaitingCopy: (copyText: string) => void,
  intervalMs = 4_000,
): GenerationRunner {
  let inFlight: Promise<GenerationResponse> | null = null;
  let timer: ReturnType<typeof setInterval> | null = null;
  let active = false;

  const stopWaiting = () => {
    active = false;
    if (timer !== null) {
      clearInterval(timer);
      timer = null;
    }
  };

  const refreshWaitingCopy = async () => {
    try {
      const copy = await api.waitingCopy();
      if (active) onWaitingCopy(copy.copy_text);
    } catch {
      // 대기 문구 실패는 실제 Generate 결과를 실패시키지 않습니다.
    }
  };

  return {
    run(pending) {
      if (inFlight !== null) return inFlight;

      active = true;
      void refreshWaitingCopy();
      timer = setInterval(() => void refreshWaitingCopy(), intervalMs);
      inFlight = api
        .generate(generationPayload(pending), pending.idempotencyKey)
        .finally(() => {
          stopWaiting();
          inFlight = null;
        });
      return inFlight;
    },
    dispose() {
      stopWaiting();
    },
  };
}

export function isBillingConfirmationRequired(error: unknown): boolean {
  if (!(error instanceof ApiError) || error.statusCode !== 409) return false;
  return (
    typeof error.detail === "object" &&
    error.detail !== null &&
    "reason" in error.detail &&
    error.detail.reason === "billing_confirmation_required"
  );
}

export async function refreshGenerationEstimate(
  api: Pick<ApiClient, "estimate">,
  pending: PendingGeneration,
  keyFactory: () => string = () => crypto.randomUUID(),
): Promise<GenerationAction> {
  const estimate = await api.estimate(pending.estimatePayload);
  return nextGenerationAction(estimate, pending.estimatePayload, keyFactory());
}

export function shouldShowFollowUpComposer(
  response: GenerationResponse | null,
): boolean {
  return response !== null && isSuccessfulGeneration(response);
}

export function FollowUpComposer({ messages, onSubmit }: { messages: FollowUpMessage[]; onSubmit: (value: string) => void }) {
  const [value, setValue] = useState("");

  function submit(event: FormEvent) {
    event.preventDefault();
    if (!value.trim()) return;
    onSubmit(value);
    setValue("");
  }

  return (
    <section className="card follow-up-card follow-up-card--wide">
      <div><p className="kicker">KEEP REFINING</p><h2>원하는 방향을 더 알려주세요</h2><p>결과를 본 뒤에도 대화로 문구와 타깃을 조정할 수 있어요.</p></div>
      {messages.length > 0 && <div className="message-list">{messages.map((message) => <div className={`message ${message.role}`} key={message.id}><span>{message.role === "user" ? "나" : "AI"}</span><p>{message.content}</p></div>)}</div>}
      <form className="follow-up-form" onSubmit={submit}><input value={value} onChange={(event) => setValue(event.target.value)} placeholder="예: 20대 고객에게 더 친근하게 바꿔줘" aria-label="추가 요청" /><button type="submit" className="primary">보내기</button></form>
    </section>
  );
}

export function GenerationLab({ api, chatbotType = "basic", initialQuestion = "", initialPurpose = "", initialSourceGenId, onStrategyToAd, onUserChanged }: { api: ApiClient; chatbotType?: ChatbotType; initialQuestion?: string; initialPurpose?: string; initialSourceGenId?: number; onStrategyToAd?: (sourceGenId: number, purpose: string) => void; onUserChanged?: (user: UserResponse) => void }) {
  const mascot = chatbotType === "basic"
    ? { name: "카피니", role: "광고 제작 파트너", src: "/assets/mascots/copyni.png" }
    : { name: "분석이", role: "상권 분석 파트너", src: "/assets/mascots/bunseoki.png" };
  const [platform, setPlatform] = useState<Platform>("instagram");
  const [question, setQuestion] = useState(initialQuestion);
  const [sourceGenId] = useState<number | null>(initialSourceGenId ?? null);
  const [extra, setExtra] = useState<GenerateExtra>({ purpose: initialPurpose || null, price_range: null, target_age: null, strength: null, clarification: null });
  const [pending, setPending] = useState<PendingGeneration | null>(null);
  const [generation, setGeneration] = useState<GenerationResponse | null>(null);
  const [messages, setMessages] = useState<FollowUpMessage[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [waiting, setWaiting] = useState(false);
  const [waitingCopy, setWaitingCopy] = useState("맞춤 결과를 준비하고 있어요.");
  const [publishedProposalIndex, setPublishedProposalIndex] =
    useState<ProposalIndex | null>(null);
  const runner = useMemo(
    () => createGenerationRunner(api, setWaitingCopy),
    [api],
  );
  useEffect(() => () => runner.dispose(), [runner]);
  const quickPrompts = chatbotType === "basic"
    ? ["여름 신메뉴를 홍보하고 싶어", "20대 고객에게 친근한 광고를 만들어줘", "주말 이벤트 문구가 필요해"]
    : ["우리 가게 매출을 늘리려면?", "주변 경쟁 가게와 차별화하려면?", "이번 달 프로모션 아이디어가 필요해"];

  function updateExtra(key: keyof GenerateExtra, value: string) {
    setPending(null);
    setExtra((current) => ({ ...current, [key]: value || null }));
  }

  async function requestEstimate(
    extraOverride: GenerateExtra = extra,
    preserveMessages = false,
    questionOverride = question,
  ) {
    if (busy) return;
    setBusy(true);
    setError(null);
    setPending(null);
    setGeneration(null);
    setPublishedProposalIndex(null);
    if (!preserveMessages) setMessages([]);
    let immediate: PendingGeneration | null = null;
    try {
      // Estimate와 Generate가 같은 생성 내용을 공유해야 승인 상한이 실제 요청과 어긋나지 않는다.
      const payload = buildEstimatePayload(
        chatbotType,
        questionOverride,
        platform,
        extraOverride,
        sourceGenId,
      );
      const response = await api.estimate(payload);
      const action = nextGenerationAction(response, payload, crypto.randomUUID());
      setPending(action.pending);
      if (action.kind === "generate") immediate = action.pending;
    } catch (caught) {
      setError(messageFrom(caught));
    } finally {
      setBusy(false);
    }
    if (immediate !== null) await generate(immediate);
  }

  async function submitFollowUp(value: string) {
    const clarification = value.trim();
    if (!clarification || busy) return;
    const nextExtra = withClarification(extra, clarification);
    setMessages((current) => [
      ...current,
      createFollowUpMessage("user", clarification, `${Date.now()}-user`),
    ]);
    setExtra(nextExtra);
    await requestEstimate(nextExtra, true);
  }

  async function estimate(event: FormEvent) {
    event.preventDefault();
    await requestEstimate();
  }

  async function generate(candidate: PendingGeneration) {
    setBusy(true);
    setWaiting(true);
    setError(null);
    let immediateRetry: PendingGeneration | null = null;
    try {
      const nextGeneration = await runner.run(candidate);
      setGeneration(nextGeneration);
      await syncUserAfterGeneration(api, onUserChanged);
    } catch (caught) {
      if (isBillingConfirmationRequired(caught)) {
        try {
          const action = await refreshGenerationEstimate(api, candidate);
          setPending(action.pending);
          if (action.kind === "generate") immediateRetry = action.pending;
        } catch (estimateError) {
          setError(messageFrom(estimateError));
        }
      } else {
        setError(messageFrom(caught));
      }
    } finally {
      setWaiting(false);
      setBusy(false);
    }
    if (immediateRetry !== null) await generate(immediateRetry);
  }

  async function publish(index: ProposalIndex, imageB64: string | null) {
    if (generation === null || busy) return;
    setBusy(true);
    setError(null);
    try {
      const published = await api.publishGeneration(generation.generation_id, {
        proposal_index: index,
        image_b64: imageB64,
      });
      setPublishedProposalIndex(published.proposal_index);
    } catch (caught) {
      setError(messageFrom(caught));
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="generation-page generation-page--wide" aria-labelledby="generation-title">
      <div className="generation-heading generation-heading-with-mascot">
        <div>
          <p className="kicker">{chatbotType === "basic" ? "BASIC CHATBOT" : "CONSULTANT CHATBOT"}</p>
          <h1 id="generation-title">{chatbotType === "basic" ? "게시물 생성" : "상권 컨설팅"}</h1>
          <strong className="mascot-role">{mascot.name} · {mascot.role}</strong>
          <p>{chatbotType === "basic" ? "구조화된 정보를 입력한 뒤 결과를 대화로 계속 다듬을 수 있습니다." : "가게와 상권에 대한 질문을 입력하고 다음 액션을 제안받아보세요."}</p>
        </div>
        <img className="generation-mascot" src={mascot.src} alt={`${mascot.name} 캐릭터`} />
      </div>

      {chatbotType === "basic" && initialSourceGenId && (
        <aside className="strategy-prefill-banner" aria-label="컨설팅 전략 연계">
          <span className="strategy-prefill-icon" aria-hidden="true">✦</span>
          <div><strong>컨설팅 전략을 이어서 만들고 있어요</strong><p>전략에 맞춰 광고 형식과 문구를 다듬어 보세요. 필요한 내용은 자유롭게 수정할 수 있습니다.</p></div>
          {initialPurpose && <span className="strategy-prefill-tag">{initialPurpose}</span>}
        </aside>
      )}

      <form className="card generation-card chat-generation-card chat-generation-card--primary" onSubmit={estimate}>
        <div className="chat-context-header"><img className="chat-avatar-image" src={mascot.src} alt="" aria-hidden="true" /><div><strong>{chatbotType === "basic" ? "어떤 광고를 만들어볼까요?" : "가게에 대해 무엇이 궁금하세요?"}</strong><p>{chatbotType === "basic" ? "첫 메시지를 보내면 광고 시안을 함께 다듬어갈게요." : "등록된 가게 정보와 상권 데이터를 바탕으로 상담할게요."}</p></div></div>
        {chatbotType === "basic" && <fieldset className="platform-picker"><legend>광고 형식</legend><div className="platform-options">
          {([['instagram', 'Instagram', '피드·릴스용'], ['xbanner', 'X-배너', '세로형 출력물']] as const).map(([value, label, hint]) => <button type="button" key={value} className={`platform-option${platform === value ? " is-active" : ""}`} aria-pressed={platform === value} onClick={() => { setPending(null); setPlatform(value); }}><strong>{label}</strong><small>{hint}</small></button>)}
        </div></fieldset>}
        {chatbotType === "basic" && platform === "xbanner" && <p className="platform-guidance" role="note"><strong>세로형 X-배너</strong>를 생성합니다. 상단 카피·비주얼과 하단 가게 정보가 하나의 세로 배너로 이어집니다.</p>}
        <label className="chat-composer-label">광고 요청
          <textarea
            value={question}
            onChange={(event) => { setPending(null); setQuestion(event.target.value); }}
            maxLength={2000}
            required
            placeholder={chatbotType === "basic" ? "예: 여름 신메뉴를 알리는 활기찬 광고를 만들어줘" : "예: 우리 카페의 매출을 늘리려면 어떻게 해야 할까요?"}
          />
        </label>
        <div className="quick-prompts" aria-label="예시 질문">{quickPrompts.map((prompt) => <button type="button" key={prompt} onClick={() => setQuestion(prompt)}>{prompt}</button>)}</div>
        {chatbotType === "basic" && <details className="extra-details">
          <summary>광고 상세 정보 추가 <span>선택사항</span></summary>
          <div className="extra-grid">
            <label>광고 목적 <small>선택</small><input value={extra.purpose ?? ""} onChange={(event) => updateExtra("purpose", event.target.value)} placeholder="신메뉴 홍보" /></label>
            <label>타깃 연령 <small>선택</small><input value={extra.target_age ?? ""} onChange={(event) => updateExtra("target_age", event.target.value)} placeholder="20~30대" /></label>
            <label>가격대 <small>선택</small><input value={extra.price_range ?? ""} onChange={(event) => updateExtra("price_range", event.target.value)} placeholder="1만원대" /></label>
            <label>가게 강점 <small>선택</small><input value={extra.strength ?? ""} onChange={(event) => updateExtra("strength", event.target.value)} placeholder="직접 만든 소스" /></label>
          </div>
        </details>}
        {chatbotType === "consultant" && <p className="generation-note">등록된 가게 정보와 상권 데이터를 바탕으로 상담을 시작합니다. 필요한 정보는 대화 중에 추가로 질문할게요.</p>}
        <button className="primary" disabled={busy}>{busy ? "확인 중…" : "예상 사용량 확인"}</button>
      </form>

      {error && <div className="error-banner wide" role="alert">{error}</div>}
      {pending && !generation && !waiting && pending.estimate.requires_confirmation && (
        <CreditDialog
          estimate={pending.estimate}
          disabled={busy}
          onConfirm={() => void generate(pending)}
          onCancel={() => setPending(null)}
        />
      )}
      {waiting && <WaitingScreen copyText={waitingCopy} chatbotType={chatbotType} platform={platform} />}
      {generation && (
        <ResultView
          response={generation}
          platform={platform}
          publishing={busy}
          publishedProposalIndex={publishedProposalIndex}
          onPublish={publish}
          onRegenerate={() => void requestEstimate()}
          onSuggestedChip={(chip) => { setPending(null); setQuestion(chip); setGeneration(null); setMessages([]); }}
          onStrategyToAd={onStrategyToAd}
          onClarification={(value) => void submitFollowUp(value)}
        />
      )}
      {shouldShowFollowUpComposer(generation) && <FollowUpComposer messages={messages} onSubmit={(value) => void submitFollowUp(value)} />}
    </section>
  );
}
