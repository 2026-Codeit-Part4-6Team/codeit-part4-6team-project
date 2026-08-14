import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";

import { ApiClient, type UserResponse } from "./api";
import { ProtectedRouteView } from "./AppRoutes";

const user: UserResponse = {
  id: 7,
  username: "owner",
  name: null,
  email: null,
  business_name: "카페 코드잇",
  business_type: "카페",
  address: "서울 강남구 역삼동",
  address_detail: null,
  road_address: null,
  lat: 37.5,
  lng: 127,
  credits: 65,
  daily_free_used: 3,
  daily_free_reset_at: null,
  daily_free_remaining: 7,
};

function renderRoute(route: "dashboard" | "basic_chatbot" | "consultant_chatbot") {
  return renderToStaticMarkup(
    <ProtectedRouteView
      api={new ApiClient()}
      user={user}
      route={route}
      onNavigate={() => undefined}
      onLogout={() => undefined}
    />,
  );
}

describe("D5 protected routes", () => {
  it("renders the dashboard as the authenticated landing page", () => {
    expect(renderRoute("dashboard")).toContain("안녕하세요, 사장님!");
  });

  it("preserves the connected estimate and generation form behind 게시물 생성", () => {
    const html = renderRoute("basic_chatbot");
    expect(html).toContain("예상 사용량 확인");
    expect(html).toContain("무엇을 만들까요?");
  });

  it("keeps the consultant route as a D5 placeholder", () => {
    const html = renderRoute("consultant_chatbot");
    expect(html).toContain("컨설턴트 챗봇");
    expect(html).toContain("다음 구현 단계에서 연결됩니다.");
  });
});
