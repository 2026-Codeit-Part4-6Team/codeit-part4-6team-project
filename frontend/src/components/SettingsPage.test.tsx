import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";

import { SettingsPage } from "./SettingsPage";

describe("SettingsPage", () => {
  it("offers three font-size choices alongside model settings", () => {
    const html = renderToStaticMarkup(<SettingsPage onBack={() => undefined} />);

    expect(html).toContain("글자 크기");
    expect(html).toContain("기본");
    expect(html).toContain("크게");
    expect(html).toContain("더 크게");
  });
});
