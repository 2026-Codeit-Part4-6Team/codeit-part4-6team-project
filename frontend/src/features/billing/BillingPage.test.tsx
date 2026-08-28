import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it, vi } from "vitest";

import { BillingPage } from "./BillingPage";

const api = {} as never;

describe("BillingPage", () => {
  it("waits for the server catalog instead of rendering a client-side price fallback", () => {
    const html = renderToStaticMarkup(<BillingPage api={api} currentCredits={0} onBack={vi.fn()} />);

    expect(html).toContain("크레딧 충전");
    expect(html).toContain("VAT 별도");
    expect(html).toContain("PG 연동 전 단계입니다");
    expect(html).toContain("가격 정보를 불러오는 중");
    expect(html).not.toContain("48,500원");
    expect(html).not.toContain("충전하기 (시연용)");
  });

});
