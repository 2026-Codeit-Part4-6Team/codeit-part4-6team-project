import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";

import { ApiClient } from "../api";
import { SettingsPage } from "./SettingsPage";
import { StoreProfilePage } from "./StoreProfilePage";

const user = {
  id: 1,
  username: "owner",
  is_admin: false,
  name: null,
  email: null,
  business_name: "코드잇 카페",
  business_type: "카페",
  address: "서울 강남구",
  address_detail: "2층",
  road_address: "서울특별시 강남구 테헤란로 152 강남파이낸스센터",
  lat: 37.5000263,
  lng: 127.0365456,
  credits: 0,
  daily_free_used: 0,
  daily_free_reset_at: null,
  daily_free_remaining: 10,
} as const;

describe("SettingsPage", () => {
  it("offers three font-size choices alongside model settings", () => {
    const html = renderToStaticMarkup(
      <SettingsPage api={new ApiClient()} user={user} onBack={() => undefined} />,
    );

    expect(html).toContain("글자 크기");
    expect(html).toContain("기본");
    expect(html).toContain("크게");
    expect(html).toContain("더 크게");
  });

  it("keeps uncontracted model choices disabled", () => {
    const html = renderToStaticMarkup(
      <SettingsPage api={new ApiClient()} user={user} onBack={() => undefined} />,
    );

    expect(html).toContain('disabled=""');
    expect(html).toContain("Provider 확정 후 제공 예정");
  });

  it("offers editable store fields from the store route", () => {
    const html = renderToStaticMarkup(
      <StoreProfilePage api={{} as never} user={user} onBack={() => undefined} />,
    );

    expect(html).toContain("가게 정보 수정");
    expect(html).toContain('value="코드잇 카페"');
    expect(html).toContain("가게 정보 저장");
    expect(html).toContain("주소 좌표와 상권 데이터의 기준");
    expect(html).toContain("주소 지도 미리보기");
    expect(html).toContain("현재 상권 분석 기준 위치");
    expect(html).toContain("naver-map-container");
    expect(html).not.toContain("openstreetmap.org");
    expect(html).toContain("강남파이낸스센터");
  });
});
