import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it, vi } from "vitest";

import { BillingPage } from "./BillingPage";

describe("BillingPage payment gate", () => {
  it("shows only unavailable package identifiers while policy is open", () => {
    const html = renderToStaticMarkup(<BillingPage onBack={vi.fn()} />);

    expect(html).toContain("결제 정책 확정 대기");
    expect(html).toContain("starter");
    expect(html).toContain("standard");
    expect(html).toContain("pro");
    expect(html).not.toMatch(/₩|원|Credit 지급|결제하기/);
    expect(html).not.toContain("결제 완료");
  });

  it("disables every package action", () => {
    const html = renderToStaticMarkup(<BillingPage onBack={vi.fn()} />);

    expect((html.match(/disabled=""/g) ?? [])).toHaveLength(3);
  });

  it("shows explicit demo prices and actions when the demo catalog is enabled", () => {
    const html = renderToStaticMarkup(
      <BillingPage
        onBack={vi.fn()}
        demoCatalog={{
          demo_enabled: true,
          packages: [
            { id: "starter", amount: 5000, credits: 500 },
            { id: "standard", amount: 10000, credits: 1100 },
            { id: "pro", amount: 30000, credits: 3500 },
          ],
        }}
      />,
    );

    expect(html).toContain("시연용 결제");
    expect(html).toContain("5,000원");
    expect(html).toContain("500 Credit");
    expect((html.match(/데모 충전/g) ?? [])).toHaveLength(3);
  });
});
