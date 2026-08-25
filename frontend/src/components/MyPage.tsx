import { useEffect, useRef, useState } from "react";

import type {
  ApiClient,
  GenerationDetailResponse,
  GenerationHistoryResponse,
  GenerationListItem,
  UserResponse,
  UserSummaryResponse,
} from "../api";
import { ErrorBanner } from "./ErrorBanner";

export function generationLabel(item: Pick<GenerationListItem, "chatbot_type">): string {
  return item.chatbot_type === "basic" ? "Basic 광고" : "Consultant";
}

export function platformLabel(platform: GenerationListItem["platform"]): string | null {
  if (platform === "instagram") return "Instagram";
  if (platform === "xbanner") return "X-배너";
  if (platform === "banner") return "배너";
  return null;
}

export function statusLabel(status: GenerationListItem["status"]): string {
  return { pending: "대기 중", generating: "생성 중", done: "완료", failed: "실패", published: "게시됨" }[status];
}

export function historyTitle(item: Pick<GenerationListItem, "title" | "question">): string {
  return item.title?.trim() || item.question;
}

function stringList(value: unknown): string[] {
  return Array.isArray(value) ? value.filter((item): item is string => typeof item === "string") : [];
}

function Detail({ detail }: { detail: GenerationDetailResponse }) {
  const result = detail.result ?? {};
  const strategy = typeof result.strategy === "object" && result.strategy !== null ? result.strategy as { summary?: unknown; actions?: unknown } : null;
  const actions = Array.isArray(strategy?.actions) ? strategy.actions.filter((raw): raw is { type?: unknown; content: string } => typeof raw === "object" && raw !== null && typeof (raw as { content?: unknown }).content === "string") : [];
  const proposals = Array.isArray(result.proposals) ? result.proposals : [];
  const reasons = stringList(result.reasons);
  const sources = stringList(result.sources);
  const blockedMessage = result.status === "blocked" && typeof result.message === "string" ? result.message : null;

  return (
    <section className="card history-detail" aria-live="polite">
      <div className="section-heading"><div><p className="kicker">GENERATION #{detail.id}</p><h2>{historyTitle(detail)}</h2></div><span className="status-chip">{statusLabel(detail.status)}</span></div>
      {detail.chatbot_type === "basic" && detail.copy_content && <div className="history-final-result">{detail.image_b64 && <img src={detail.image_b64} alt="게시 승인된 최종 이미지" />}<div><span>최종 게시 문구</span><p>{detail.copy_content}</p></div></div>}
      {detail.chatbot_type === "basic" && !detail.copy_content && proposals.length > 0 && <ol className="history-proposals">{proposals.map((raw, index) => { const proposal = typeof raw === "object" && raw !== null ? raw as { copy?: unknown; error?: { message?: unknown } | null } : {}; const text = typeof proposal.copy === "string" ? proposal.copy : typeof proposal.error?.message === "string" ? proposal.error.message : "결과 없음"; return <li key={index}>{text}</li>; })}</ol>}
      {detail.chatbot_type === "consultant" && typeof strategy?.summary === "string" && <p className="strategy-summary">{strategy.summary}</p>}
      {detail.chatbot_type === "consultant" && actions.length > 0 && <div className="history-evidence"><strong>실행 제안</strong><ul>{actions.map((action, index) => <li key={`${String(action.type)}-${index}`}>{action.content}</li>)}</ul></div>}
      {reasons.length > 0 && <div className="history-evidence"><strong>제안 이유</strong><ul>{reasons.map((reason) => <li key={reason}>{reason}</li>)}</ul></div>}
      {sources.length > 0 && <div className="history-evidence"><strong>참고 근거</strong><ul>{sources.map((source) => <li key={source}>{source}</li>)}</ul></div>}
      {blockedMessage && <p className="history-blocked">{blockedMessage}</p>}
    </section>
  );
}

export type MyPageViewProps = {
  user: UserResponse;
  summary: UserSummaryResponse | null;
  history: GenerationListItem[];
  detail: GenerationDetailResponse | null;
  loading: boolean;
  detailLoading: boolean;
  error: unknown;
  onSelect: (id: number) => void;
  onBack: () => void;
  onBilling?: () => void;
  historyPage?: Pick<GenerationHistoryResponse, "page" | "page_size" | "total" | "total_pages">;
  historyQuery?: string;
  onHistoryQueryChange?: (query: string) => void;
  onHistoryPageChange?: (page: number) => void;
};

export function MyPageView({
  user,
  summary,
  history,
  detail,
  loading,
  detailLoading,
  error,
  onSelect,
  onBack,
  onBilling,
  historyPage = { page: 1, page_size: 10, total: history.length, total_pages: history.length > 0 ? 1 : 0 },
  historyQuery = "",
  onHistoryQueryChange,
  onHistoryPageChange,
}: MyPageViewProps) {
  const [expandedId, setExpandedId] = useState<number | null>(detail?.id ?? null);

  useEffect(() => {
    setExpandedId(null);
  }, [historyQuery, historyPage.page]);

  function toggleGeneration(id: number) {
    if (expandedId === id) {
      setExpandedId(null);
      return;
    }
    setExpandedId(id);
    onSelect(id);
  }

  return (
    <section className="account-page" aria-labelledby="mypage-title">
      <button type="button" className="back-link" onClick={onBack}>← 대시보드로 돌아가기</button>
      <div className="page-heading"><p className="kicker">MY PAGE</p><h1 id="mypage-title">내 활동을 한눈에 확인하세요.</h1><p>{user.business_name ?? user.username}님의 생성 기록과 사용 현황입니다.</p></div>
      <div className="summary-grid"><div className="stat-card"><span>현재 Credit</span><strong>{summary?.credits ?? "—"}</strong></div><div className="stat-card"><span>오늘 무료 생성 잔여</span><strong>{summary?.daily_free_remaining ?? "—"}</strong></div><div className="stat-card"><span>전체 생성 <small>(실데이터)</small></span><strong>{summary?.total_generations ?? "—"}</strong></div><div className="stat-card"><span>게시 완료 <small>(실데이터)</small></span><strong>{summary?.published_generations ?? "—"}</strong></div></div>
      {error !== null && error !== undefined && <ErrorBanner error={error} onBilling={onBilling} />}
      <section className="card history-card">
        <div className="section-heading"><div><p className="kicker">RECENT ACTIVITY</p><h2>최근 생성 기록</h2></div></div>
        <div className="history-toolbar">
          <label htmlFor="history-search">생성 기록 검색</label>
          <input
            id="history-search"
            type="search"
            value={historyQuery}
            placeholder="제목이나 요청 내용으로 찾아보세요"
            onChange={(event) => onHistoryQueryChange?.(event.target.value)}
          />
          {historyPage.total > 0 && <span className="history-count">총 {historyPage.total}건</span>}
        </div>
      {loading ? <p className="history-state" role="status">활동 기록을 불러오는 중…</p> : error !== null && error !== undefined ? null : history.length === 0 ? <p className="history-state">{historyQuery.trim() ? "조건에 맞는 생성 기록이 없습니다." : "아직 생성 기록이 없습니다."}</p> : <div className="history-list">{history.map((item) => { const expanded = expandedId === item.id; const platform = platformLabel(item.platform); return <div className={`history-item${expanded ? " is-expanded" : ""}`} key={item.id}><button type="button" className="history-row history-item-card" aria-expanded={expanded} aria-controls={`history-detail-${item.id}`} onClick={() => toggleGeneration(item.id)}><div className="history-row-main"><div className="history-row-badges"><span className="history-type-chip">{generationLabel(item)}</span>{platform && <span className="history-platform-chip">{platform}</span>}</div><strong>{historyTitle(item)}</strong><small className="history-row-date">{new Date(item.created_at).toLocaleDateString("ko-KR")}</small></div><div className="history-row-meta"><span className={`status-chip status-chip--${item.status}`}>{statusLabel(item.status)}</span><small>{item.credits_used} Credit</small><small className="history-expand-hint">{expanded ? "접기 ↑" : "상세 보기 ↓"}</small></div></button>{expanded && <div className="history-inline-detail" id={`history-detail-${item.id}`}>{detailLoading && <p className="history-state" role="status">상세 결과를 불러오는 중…</p>}{detail && !detailLoading && detail.id === item.id && <Detail detail={detail} />}</div>}</div>; })}</div>}
      {!loading && error === null && historyPage.total_pages > 1 && <nav className="history-pagination" aria-label="생성 기록 페이지 이동"><button type="button" disabled={historyPage.page <= 1} onClick={() => onHistoryPageChange?.(historyPage.page - 1)}>이전</button><span>{historyPage.page} / {historyPage.total_pages}</span><button type="button" disabled={historyPage.page >= historyPage.total_pages} onClick={() => onHistoryPageChange?.(historyPage.page + 1)}>다음</button></nav>}
      </section>
      {history.length === 0 && detail && !detailLoading && <Detail detail={detail} />}
    </section>
  );
}

export function MyPage({ api, user, onBack, onBilling }: { api: ApiClient; user: UserResponse; onBack: () => void; onBilling?: () => void }) {
  const [summary, setSummary] = useState<UserSummaryResponse | null>(null);
  const [history, setHistory] = useState<GenerationListItem[]>([]);
  const [historyPage, setHistoryPage] = useState<Pick<GenerationHistoryResponse, "page" | "page_size" | "total" | "total_pages">>({ page: 1, page_size: 10, total: 0, total_pages: 0 });
  const [historyQuery, setHistoryQuery] = useState("");
  const [requestedPage, setRequestedPage] = useState(1);
  const [detail, setDetail] = useState<GenerationDetailResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [detailLoading, setDetailLoading] = useState(false);
  const [error, setError] = useState<unknown>(null);
  const detailRequest = useRef(0);

  useEffect(() => {
    let active = true;
    setLoading(true);
    setError(null);
    const timer = window.setTimeout(() => {
      api.generationHistoryPage({ query: historyQuery, page: requestedPage }).then((response) => {
        if (active) {
          setHistory(response.items);
          setHistoryPage(response);
        }
      }).catch((caught: unknown) => { if (active) setError(caught); }).finally(() => { if (active) setLoading(false); });
    }, 300);
    return () => { active = false; detailRequest.current += 1; window.clearTimeout(timer); };
  }, [api, historyQuery, requestedPage]);

  useEffect(() => {
    let active = true;
    api.userSummary().then((response) => { if (active) setSummary(response); }).catch((caught: unknown) => { if (active) setError(caught); });
    return () => { active = false; };
  }, [api]);

  function changeHistoryQuery(query: string) {
    setHistoryQuery(query);
    setRequestedPage(1);
    setDetail(null);
  }

  function changeHistoryPage(page: number) {
    setRequestedPage(page);
    setDetail(null);
  }

  function selectGeneration(id: number) {
    const request = ++detailRequest.current;
    setDetailLoading(true);
    setDetail(null);
    setError(null);
    api.generationDetail(id).then((nextDetail) => { if (detailRequest.current === request) setDetail(nextDetail); }).catch((caught: unknown) => { if (detailRequest.current === request) setError(caught); }).finally(() => { if (detailRequest.current === request) setDetailLoading(false); });
  }

  return <MyPageView user={user} summary={summary} history={history} historyPage={historyPage} historyQuery={historyQuery} onHistoryQueryChange={changeHistoryQuery} onHistoryPageChange={changeHistoryPage} detail={detail} loading={loading} detailLoading={detailLoading} error={error} onSelect={selectGeneration} onBack={onBack} onBilling={onBilling} />;
}
