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
    expect(html).toMatch(/<button[^>]*disabled=""[^>]*>선택 불가<\/button>/);
    expect(html).toContain("다시 생성");
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
      />,
    );

    expect(html).not.toContain("게시 승인");
    expect(html).not.toContain("이 제안 선택");
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
