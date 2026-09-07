import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it, vi } from "vitest";

import type { GenerationResponse } from "../../api";
import { ResultView } from "./ResultView";

const basicResponse: GenerationResponse = {
  generation_id: 7,
  status: "done",
  chatbot_type: "basic",
  result: {
    status: "ok",
    title: "광고 제안",
    proposals: [
      { copy: "첫 제안", image_b64: "encoded", error: null },
      {
        copy: null,
        image_b64: null,
        error: { field: "copy", reason: "unknown", message: "생성 실패" },
      },
      { copy: "세 번째 제안", image_b64: null, error: null },
    ],
  },
  usage: { plan: "free", credits_used: 0 },
};

describe("ResultView", () => {
  const blockedResponse = (reason: string, message = "검증 결과를 확인해 주세요."): GenerationResponse => ({
    generation_id: 9,
    status: "failed",
    chatbot_type: "basic",
    result: {
      status: "blocked",
      action: reason === "regulation_risk" ? "warn" : reason === "need_clarification" || reason === "insufficient_info" ? "reask" : "block",
      reason,
      message,
    },
    usage: { plan: "free", credits_used: 0 },
  });

  it("preserves three Basic slots and disables a slot without copy", () => {
    const html = renderToStaticMarkup(
      <ResultView
        response={basicResponse}
        onPublish={vi.fn()}
        onRegenerate={vi.fn()}
      />,
    );

    expect(html).toContain("제안 1");
    expect(html).toContain("제안 2");
    expect(html).toContain("제안 3");
    expect(html).toContain("생성 실패");
    expect(html).toContain('class="proposal-action" disabled=""');
    expect(html).toContain("선택 불가");
    expect(html).toContain("다시 생성");
    expect(html).toContain('class="result-action-buttons"');
    expect(html).toContain('class="action-button action-button-secondary regenerate-action"');
  });

  it("does not render publish controls for Consultant results", () => {
    const html = renderToStaticMarkup(
      <ResultView
        response={{
          generation_id: 8,
          status: "done",
          chatbot_type: "consultant",
          result: {
            status: "ok",
            title: "상권 전략",
            strategy: { summary: "요약", actions: [] },
          },
          usage: { plan: "paid", credits_used: 10 },
        }}
        onPublish={vi.fn()}
        onRegenerate={vi.fn()}
        onStrategyToAd={vi.fn()}
      />,
    );

    expect(html).not.toContain("게시 승인");
    expect(html).not.toContain("이 제안 선택");
    expect(html).toContain("이 전략으로 광고 만들기");
    expect(html).toContain("다시 생성");
  });

  it("marks the approved proposal as published", () => {
    const html = renderToStaticMarkup(
      <ResultView
        response={basicResponse}
        publishedProposalIndex={2}
        onPublish={vi.fn()}
        onRegenerate={vi.fn()}
      />,
    );

    expect(html).toContain("게시 승인 완료");
    expect(html).toContain("제안 3 게시됨");
    expect(html).toContain('class="proposal-action is-published"');
  });

  it("passes X-banner presentation through to the result cards", () => {
    const html = renderToStaticMarkup(
      <ResultView
        response={basicResponse}
        platform="xbanner"
        onPublish={vi.fn()}
        onRegenerate={vi.fn()}
      />,
    );

    expect(html).toContain('class="result-section result-section--xbanner"');
    expect(html).toContain("세로형 X-배너");
    expect(html).toContain('class="card proposal proposal--xbanner"');
  });

  it.each(["basic", "consultant"] as const)(
    "shows the exact blocked message without result controls for %s",
    (chatbotType) => {
      const html = renderToStaticMarkup(
        <ResultView
          response={{
            generation_id: 9,
            status: "failed",
            chatbot_type: chatbotType,
            result: {
              status: "blocked",
              action: "reask",
              reason: "정보 부족",
              message: "가게의 대표 메뉴를 알려주세요.",
            },
            usage: { plan: "free", credits_used: 0 },
          }}
          onPublish={vi.fn()}
          onRegenerate={vi.fn()}
        />,
      );

      expect(html).toContain("가게의 대표 메뉴를 알려주세요.");
      expect(html).not.toContain("이 제안 선택");
      expect(html).not.toContain("게시 승인");
      expect(html).not.toContain("전략 요약이 없습니다");
    },
  );

  it("passes through a non-success result message even when its reason is not yet specialized", () => {
    const html = renderToStaticMarkup(
      <ResultView
        response={{
          generation_id: 10,
          status: "failed",
          chatbot_type: "basic",
          result: {
            status: "error",
            reason: "content_policy",
            message: "'최고'는 부당광고가 될 수 있어요. 대신 다른 표현을 사용해 주세요.",
          },
          usage: { plan: "free", credits_used: 0 },
        }}
        onPublish={vi.fn()}
        onRegenerate={vi.fn()}
      />,
    );

    expect(html).toContain("대신 다른 표현을 사용해 주세요.");
    expect(html).not.toContain("생성 결과를 표시할 수 없습니다");
    expect(html).not.toContain("결과가 없습니다");
  });

  it.each([
    ["illegal_or_injection", "질문을 다시 입력해 주세요", true],
    ["need_clarification", "조금만 더 알려주세요", true],
    ["insufficient_info", "조금만 더 알려주세요", true],
    ["prohibited_item", "생성을 중단했어요", false],
    ["regulation_risk", "대안 표현을 확인해 주세요", false],
    ["sensitive_leak", "생성을 중단했어요", false],
  ] as const)(
    "renders the §12.3 policy treatment for %s",
    (reason, heading, hasClarificationForm) => {
      const html = renderToStaticMarkup(
        <ResultView
          response={blockedResponse(reason, `${reason} 안내 메시지`)}
          onPublish={vi.fn()}
          onRegenerate={vi.fn()}
          onClarification={vi.fn()}
        />,
      );

      expect(html).toContain(heading);
      expect(html).toContain(`${reason} 안내 메시지`);
      if (hasClarificationForm) {
        expect(html).toContain("추가 답변");
        expect(html).toContain("이 내용으로 이어서 만들기");
      } else {
        expect(html).not.toContain("이 내용으로 이어서 만들기");
      }
      if (reason === "regulation_risk") {
        expect(html).toContain("다시 만들기");
      }
    },
  );

  it("keeps a successful content-policy slot selectable", () => {
    const html = renderToStaticMarkup(
      <ResultView
        response={{
          ...basicResponse,
          result: {
            ...basicResponse.result,
            proposals: [
              {
                copy: "정책에 맞게 조정한 문구",
                image_b64: null,
                error: {
                  field: "image",
                  reason: "content_policy",
                  message: "이미지만 제외했습니다.",
                },
              },
            ],
          },
        }}
        onPublish={vi.fn()}
        onRegenerate={vi.fn()}
      />,
    );

    expect(html).toContain("정책에 맞게 조정한 문구");
    expect(html).toContain("이 제안 선택");
  });
});
