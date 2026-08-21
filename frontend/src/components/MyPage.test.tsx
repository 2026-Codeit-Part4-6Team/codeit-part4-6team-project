import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it, vi } from "vitest";

import {
  ApiError,
  type GenerationDetailResponse,
  type GenerationListItem,
  type UserResponse,
  type UserSummaryResponse,
} from "../api";
import {
  generationLabel,
  historyTitle,
  MyPageView,
  statusLabel,
} from "./MyPage";

const user: UserResponse = {
  id: 1,
  username: "owner",
  name: null,
  email: null,
  business_name: "코드잇 카페",
  business_type: "카페",
  address: "서울 강남구",
  address_detail: null,
  road_address: null,
  lat: 37.5,
  lng: 127,
  credits: 1,
  daily_free_used: 1,
  daily_free_reset_at: null,
  daily_free_remaining: 1,
};

const summary: UserSummaryResponse = {
  credits: 125,
  daily_free_remaining: 8,
  total_generations: 2,
  published_generations: 1,
};

const history: GenerationListItem[] = [
  {
    id: 2,
    chatbot_type: "consultant",
    title: "상권 전략",
    question: "상권을 알려줘",
    platform: null,
    plan: "paid",
    credits_used: 10,
    tokens_used: 5,
    status: "done",
    created_at: "2026-08-21T01:00:00Z",
  },
  {
    id: 1,
    chatbot_type: "basic",
    title: null,
    question: "광고를 만들어줘",
    platform: "instagram",
    plan: "free",
    credits_used: 0,
    tokens_used: 3,
    status: "published",
    created_at: "2026-08-20T01:00:00Z",
  },
];

function renderView(
  overrides: Partial<Parameters<typeof MyPageView>[0]> = {},
): string {
  return renderToStaticMarkup(
    <MyPageView
      user={user}
      summary={summary}
      history={history}
      detail={null}
      loading={false}
      detailLoading={false}
      error={null}
      onSelect={vi.fn()}
      onBack={vi.fn()}
      {...overrides}
    />,
  );
}

describe("MyPage presentation", () => {
  it("uses stable user-facing labels and question fallback", () => {
    expect(generationLabel({ chatbot_type: "basic" })).toBe("Basic 광고");
    expect(generationLabel({ chatbot_type: "consultant" })).toBe("Consultant");
    expect(statusLabel("published")).toBe("게시됨");
    expect(historyTitle(history[1])).toBe("광고를 만들어줘");
  });

  it("renders server summary and preserves server history order", () => {
    const html = renderView();

    expect(html).toContain("125");
    expect(html).toContain("8");
    expect(html).toContain("2");
    expect(html).toContain("1");
    expect(html.indexOf("상권 전략")).toBeLessThan(html.indexOf("광고를 만들어줘"));
    expect(html).not.toContain("스토리보드 데이터");
  });

  it("renders loading, empty, and safe error states", () => {
    expect(renderView({ loading: true, summary: null, history: [] })).toContain(
      "활동 기록을 불러오는 중",
    );
    expect(renderView({ history: [] })).toContain("아직 생성 기록이 없습니다");

    const html = renderView({
      error: new ApiError(500, { stack: "Traceback secret-api-key" }),
    });
    expect(html).toContain("서비스 연결이 불안정합니다");
    expect(html).not.toContain("secret-api-key");
  });

  it("renders published Basic final copy and image without internal keys", () => {
    const detail: GenerationDetailResponse = {
      ...history[1],
      source_gen_id: null,
      result: null,
      copy_content: "최종 광고 문구",
      image_b64: "data:image/png;base64,aW1hZ2U=",
      selected_proposal_index: 1,
      hitl_approved: true,
    };
    const html = renderView({ detail });

    expect(html).toContain("최종 광고 문구");
    expect(html).toContain("data:image/png;base64,aW1hZ2U=");
    expect(html).not.toContain("request_hash");
    expect(html).not.toContain("idempotency_key");
    expect(html).not.toContain("result_json");
  });

  it("renders Consultant strategy, reasons, and sources", () => {
    const detail: GenerationDetailResponse = {
      ...history[0],
      source_gen_id: null,
      result: {
        status: "ok",
        title: "상권 전략",
        strategy: { summary: "직장인 고객 집중", actions: [] },
        reasons: ["오피스 상권"],
        sources: ["상권 API"],
      },
      copy_content: null,
      image_b64: null,
      selected_proposal_index: null,
      hitl_approved: false,
    };
    const html = renderView({ detail });

    expect(html).toContain("직장인 고객 집중");
    expect(html).toContain("오피스 상권");
    expect(html).toContain("상권 API");
  });
});
