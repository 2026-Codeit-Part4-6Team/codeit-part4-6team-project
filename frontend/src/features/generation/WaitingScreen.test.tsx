import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";

import { WaitingScreen } from "./WaitingScreen";

describe("WaitingScreen", () => {
  it("renders the latest server-managed waiting copy", () => {
    const html = renderToStaticMarkup(
      <WaitingScreen copyText="카페에 어울리는 문구를 다듬고 있어요." />,
    );

    expect(html).toContain("카페에 어울리는 문구를 다듬고 있어요.");
    expect(html).toContain("생성 중");
  });

  it("renders a consultant example carousel while waiting", () => {
    const html = renderToStaticMarkup(
      <WaitingScreen
        copyText="상권 데이터를 읽고 있어요."
        chatbotType="consultant"
        platform="instagram"
      />,
    );

    expect(html).toContain("예시 미리보기");
    expect(html).toContain("전략 예시 1/3");
    expect(html).toContain("상권 전략");
  });

  it("renders a platform-shaped Basic preview while waiting", () => {
    const html = renderToStaticMarkup(
      <WaitingScreen
        copyText="카피니가 문구를 다듬고 있어요."
        chatbotType="basic"
        platform="xbanner"
      />,
    );

    expect(html).toContain("X-배너 예시 1/3");
    expect(html).toContain("예시 미리보기");
    expect(html).toContain("세로형");
  });
});
