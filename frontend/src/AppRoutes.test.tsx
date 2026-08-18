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

function renderRoute(route: "dashboard" | "basic_chatbot" | "consultant_chatbot" | "mypage" | "billing" | "settings") {
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
    expect(html).toContain("첫 메시지");
    expect(html).toContain("첫 메시지");
    expect(html).not.toContain("상권 컨설팅");
  });

  it("renders the consultant input surface without a platform selector", () => {
    const html = renderRoute("consultant_chatbot");
    expect(html).toContain("상권 컨설팅");
    expect(html).toContain("등록된 가게 정보와 상권 데이터를 바탕으로 상담을 시작합니다.");
    expect(html).toContain("우리 가게 매출을 늘리려면?");
    expect(html).not.toContain("광고 목적");
    expect(html).not.toContain("광고 형식");
  });

  it("renders the storyboard account surfaces", () => {
    expect(renderRoute("mypage")).toContain("최근 생성 기록");
    expect(renderRoute("settings")).toContain("사용할 AI 모델");
    expect(renderRoute("settings")).toContain("GPT");
    expect(renderRoute("settings")).toContain("Claude");
  });
});
