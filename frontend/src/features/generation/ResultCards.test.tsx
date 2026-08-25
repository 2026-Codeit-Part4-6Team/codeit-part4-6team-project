import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";

import { ResultCards } from "./ResultCards";

describe("ResultCards", () => {
  it("keeps three Basic proposal slots even when the response is partial", () => {
    const html = renderToStaticMarkup(
      <ResultCards
        response={{
          generation_id: 2,
          status: "done",
          chatbot_type: "basic",
          result: { proposals: [{ copy: "첫 번째 제안" }] },
          usage: { plan: "free", credits_used: 0 },
        }}
      />,
    );

    expect(html).toContain("제안 1");
    expect(html).toContain("제안 2");
    expect(html).toContain("제안 3");
  });

  it("renders consultant actions as labeled strategy cards with collapsible evidence", () => {
    const html = renderToStaticMarkup(
      <ResultCards
        response={{
          generation_id: 1,
          status: "done",
          chatbot_type: "consultant",
          result: {
            title: "상권 전략",
            strategy: { summary: "요약", actions: [{ type: "menu", content: "대표 메뉴를 정리하세요." }] },
            reasons: ["주변 상권의 점심 수요가 높습니다."],
            sources: ["상권 분석 데이터"],
          },
          usage: { plan: "free", credits_used: 0 },
        }}
      />,
    );

    expect(html).toContain("핵심 상품/서비스");
    expect(html).toContain("이렇게 제안한 이유");
    expect(html).toContain("참고 근거");
    expect(html).toContain("<details");
    expect(html).not.toContain(">menu<");
  });
});
