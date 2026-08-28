import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it, vi } from "vitest";

import { CreditDialog } from "./CreditDialog";

describe("CreditDialog", () => {
  it("shows the server estimate and explicit paid consent actions", () => {
    const html = renderToStaticMarkup(
      <CreditDialog
        estimate={{
          is_free: false,
          free_remaining: 0,
          estimated_credits: 50,
          current_credits: 120,
          credits_after: 70,
          requires_confirmation: true,
        }}
        onConfirm={vi.fn()}
        onCancel={vi.fn()}
      />,
    );

    expect(html).toContain("50 Credit");
    expect(html).toContain("120 Credit");
    expect(html).toContain("70 Credit");
    expect(html).toContain("동의하고 생성");
    expect(html).toContain("취소");
    expect(html).toContain('class="credit-dialog-header"');
    expect(html).toContain('class="dialog-button dialog-button-primary"');
    expect(html).toContain('class="dialog-button dialog-button-secondary"');
  });

  it("does not ask for consent on a free estimate", () => {
    const html = renderToStaticMarkup(
      <CreditDialog
        estimate={{ estimated_credits: 0, requires_confirmation: false }}
        onConfirm={vi.fn()}
        onCancel={vi.fn()}
      />,
    );

    expect(html).toBe("");
  });
});
