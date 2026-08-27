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
});
