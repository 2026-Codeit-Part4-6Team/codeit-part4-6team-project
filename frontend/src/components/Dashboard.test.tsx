import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";

import type { UserResponse } from "../api";
import { DashboardHome } from "./DashboardHome";
import { DashboardLayout } from "./DashboardLayout";

const user: UserResponse = {
  id: 7,
  username: "owner",
  name: "김사장",
  email: null,
  business_name: "카페 코드잇",
  business_type: "카페",
  address: "서울 강남구 역삼동",
  address_detail: "2층",
  road_address: "서울 강남구 테헤란로 1",
  lat: 37.5,
  lng: 127.0,
  credits: 65,
  daily_free_used: 3,
  daily_free_reset_at: null,
  daily_free_remaining: 7,
};

describe("D5 dashboard", () => {
  it("renders backend-owned store and usage data with the two D5 entry cards", () => {
    const html = renderToStaticMarkup(
      <DashboardLayout
        user={user}
        route="dashboard"
        onNavigate={() => undefined}
        onLogout={() => undefined}
      >
        <DashboardHome onNavigate={() => undefined} />
      </DashboardLayout>,
    );

    expect(html).toContain("카페 코드잇");
    expect(html).toContain("서울 강남구 테헤란로 1 2층");
    expect(html).toContain("65");
    expect(html).toContain("7회 남음");
    expect(html).toContain("컨설턴트 챗봇");
    expect(html).toContain("게시물 생성");
    expect(html).not.toContain("블로그");
  });

  it("falls back to the registered address when no road address exists", () => {
    const html = renderToStaticMarkup(
      <DashboardLayout
        user={{ ...user, road_address: null, address_detail: null }}
        route="dashboard"
        onNavigate={() => undefined}
        onLogout={() => undefined}
      >
        <DashboardHome onNavigate={() => undefined} />
      </DashboardLayout>,
    );

    expect(html).toContain("서울 강남구 역삼동");
  });
});
