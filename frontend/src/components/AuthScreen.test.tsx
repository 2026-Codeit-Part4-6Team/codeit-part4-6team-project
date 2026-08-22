import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";

import { ApiClient } from "../api";
import { AuthScreen } from "./AuthScreen";

describe("AuthScreen", () => {
  it("renders the Figma-aligned login hierarchy without the POC split hero", () => {
    const html = renderToStaticMarkup(
      <AuthScreen api={new ApiClient()} onAuthenticated={() => undefined} />,
    );

    expect(html).toContain("매출부스터");
    expect(html).toContain("소상공인을 위한 AI 마케팅 어시스턴트");
    expect(html).toContain("사용자명");
    expect(html).toContain("비밀번호");
    expect(html).toContain("회원가입");
    expect(html).not.toContain("FIRST GENERATION POC");
    expect(html).not.toContain("가게를 등록하고");
  });

  it("uses the sales booster logo and both mascots on the login screen", () => {
    const html = renderToStaticMarkup(
      <AuthScreen api={new ApiClient()} onAuthenticated={() => undefined} />,
    );

    expect(html).toContain("/assets/brand/salesbooster-logo.png");
    expect(html).toContain("/assets/mascots/copyni.png");
    expect(html).toContain("/assets/mascots/bunseoki.png");
    expect(html).not.toContain("<figcaption>");
  });
});
