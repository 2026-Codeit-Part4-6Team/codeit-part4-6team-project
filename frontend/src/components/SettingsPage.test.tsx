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
  road_address: null,
  lat: null,
  lng: null,
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

  it("offers editable store fields from the store route", () => {
    const html = renderToStaticMarkup(
      <StoreProfilePage api={{} as never} user={user} onBack={() => undefined} />,
    );

    expect(html).toContain("가게 정보 수정");
    expect(html).toContain('value="코드잇 카페"');
    expect(html).toContain("가게 정보 저장");
    expect(html).toContain("주소 좌표와 상권 데이터의 기준");
  });
});
