import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it, vi } from "vitest";

import { ApiError } from "../api";
import { ErrorBanner } from "./ErrorBanner";

describe("ErrorBanner", () => {
  it("shows a safe Credit shortage with a billing action", () => {
    const html = renderToStaticMarkup(
      <ErrorBanner
        error={new ApiError(402, { required: 50, current: 10 })}
        onBilling={vi.fn()}
      />,
    );

    expect(html).toContain("Credit이 부족합니다");
    expect(html).toContain("충전 화면으로 이동");
  });

  it("shows retry guidance for rate limits", () => {
    const html = renderToStaticMarkup(
      <ErrorBanner error={new ApiError(429, { reason: "rate_limit" })} />,
    );

    expect(html).toContain("잠시 후 다시 시도");
  });

  it("never renders backend secrets or stack details", () => {
    const secret = "NCP_API_KEY=secret-value\nTraceback: provider.py:42";
    const html = renderToStaticMarkup(
      <ErrorBanner error={new ApiError(503, { message: secret })} />,
    );

    expect(html).toContain("서비스 연결이 불안정합니다");
    expect(html).not.toContain("secret-value");
    expect(html).not.toContain("Traceback");
  });

  it("uses safe guidance for conflicts and validation", () => {
    expect(
      renderToStaticMarkup(<ErrorBanner error={new ApiError(409, {})} />),
    ).toContain("최신 상태를 다시 확인");
    expect(
      renderToStaticMarkup(<ErrorBanner error={new ApiError(422, {})} />),
    ).toContain("입력값을 확인");
  });
});
