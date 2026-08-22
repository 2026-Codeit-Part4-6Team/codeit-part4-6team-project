import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it, vi } from "vitest";

import { BillingPage } from "./BillingPage";

const api = {} as never;

describe("BillingPage", () => {
  it("shows the confirmed credit policy and purchase actions", () => {
    const html = renderToStaticMarkup(<BillingPage api={api} currentCredits={0} onBack={vi.fn()} />);

    expect(html).toContain("크레딧 충전");
    expect(html).toContain("starter");
    expect(html).toContain("standard");
    expect(html).toContain("pro");
    expect(html).toContain("48,500원");
    expect(html).toContain("93,000원");
    expect(html).toContain("180,000원");
    expect(html).toContain("VAT 별도");
    expect(html).toContain("결제하기");
  });
});
