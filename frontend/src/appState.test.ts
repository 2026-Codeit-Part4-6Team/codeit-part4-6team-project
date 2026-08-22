import { describe, expect, it } from "vitest";

import type { UserResponse } from "./api";
import { authenticatedState, loggedOutState, navigate, startBasicFromStrategy } from "./appState";

const user: UserResponse = {
  id: 7,
  username: "owner",
  is_admin: false,
  name: "김사장",
  email: null,
  business_name: "카페 코드잇",
  business_type: "카페",
  address: "서울 강남구 역삼동",
  address_detail: null,
  road_address: "서울 강남구 테헤란로",
  lat: 37.5,
  lng: 127.0,
  credits: 65,
  daily_free_used: 3,
  daily_free_reset_at: null,
  daily_free_remaining: 7,
};

describe("D5 application view state", () => {
  it("starts an authenticated user on the dashboard", () => {
    expect(authenticatedState(user)).toEqual({ user, route: "dashboard" });
  });

  it("navigates to the preserved generation screen without replacing the user", () => {
    expect(navigate(authenticatedState(user), "basic_chatbot")).toEqual({
      user,
      route: "basic_chatbot",
    });
  });

  it("opens Basic with the server-owned consultant generation reference", () => {
    expect(startBasicFromStrategy(authenticatedState(user), 42)).toEqual({
      user,
      route: "basic_chatbot",
      generationPrefill: {
        source_gen_id: 42,
        question: "이 전략으로 광고를 만들어줘",
      },
    });
  });

  it("clears protected state on logout", () => {
    expect(loggedOutState()).toEqual({ user: null, route: "dashboard" });
  });
});
