import { describe, expect, it } from "vitest";

import { ApiError, type UserResponse } from "./api";
import {
  authErrorMessage,
  buildRegisterPayload,
  RegistrationCompletedLoginFailed,
  registerAndLogin,
  type RegistrationFields,
} from "./auth";

const validFields: RegistrationFields = {
  username: " Owner ",
  password: "safe-password",
  passwordConfirm: "safe-password",
  name: "",
  email: "",
  businessName: "코드잇 카페",
  businessType: "카페",
  address: "서울 강남구 테헤란로 1",
  addressDetail: "",
};

const user: UserResponse = {
  id: 1,
  username: "owner",
  name: null,
  email: null,
  business_name: "코드잇 카페",
  business_type: "카페",
  address: "서울 강남구 테헤란로 1",
  address_detail: null,
  road_address: "서울 강남구 테헤란로 1",
  lat: 37.4979,
  lng: 127.0276,
  credits: 0,
  daily_free_used: 0,
  daily_free_reset_at: "2026-08-14T15:00:00Z",
  daily_free_remaining: 10,
  is_admin: false,
};

describe("registration contract", () => {
  it("builds the backend payload without password confirmation", () => {
    expect(buildRegisterPayload(validFields)).toEqual({
      username: "owner",
      password: "safe-password",
      name: null,
      email: null,
      business_name: "코드잇 카페",
      business_type: "카페",
      address: "서울 강남구 테헤란로 1",
      address_detail: null,
    });
  });

  it("rejects a mismatched password confirmation", () => {
    expect(() =>
      buildRegisterPayload({ ...validFields, passwordConfirm: "different-password" }),
    ).toThrow("비밀번호가 일치하지 않습니다.");
  });

  it("rejects a password outside the backend UTF-8 byte range", () => {
    expect(() =>
      buildRegisterPayload({ ...validFields, password: "짧음", passwordConfirm: "짧음" }),
    ).toThrow("비밀번호는 UTF-8 기준 8~72바이트여야 합니다.");
  });

  it("registers before logging in and returns the authenticated user", async () => {
    const events: string[] = [];
    const api = {
      async register() {
        events.push("register");
        return user;
      },
      async login() {
        events.push("login");
        return user;
      },
    };

    await expect(registerAndLogin(api, validFields)).resolves.toEqual(user);
    expect(events).toEqual(["register", "login"]);
  });

  it("preserves the username when registration succeeded but login failed", async () => {
    const api = {
      async register() {
        return user;
      },
      async login(): Promise<UserResponse> {
        throw new ApiError(503, { code: "temporary" });
      },
    };

    await expect(registerAndLogin(api, validFields)).rejects.toEqual(
      new RegistrationCompletedLoginFailed("owner"),
    );
  });
});

describe("authErrorMessage", () => {
  it("maps duplicate usernames without exposing the raw response", () => {
    expect(
      authErrorMessage(
        new ApiError(409, { code: "duplicate_username", message: "raw backend message" }),
      ),
    ).toBe("이미 사용 중인 사용자명입니다.");
  });

  it("uses the D5 login guidance for invalid credentials", () => {
    expect(authErrorMessage(new ApiError(401, {}))).toBe(
      "사용자명 또는 비밀번호를 확인해 주세요.",
    );
  });
});
