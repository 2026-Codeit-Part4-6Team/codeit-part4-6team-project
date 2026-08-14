import { ApiError, type UserResponse } from "./api";

export type RegistrationFields = {
  username: string;
  password: string;
  passwordConfirm: string;
  name: string;
  email: string;
  businessName: string;
  businessType: string;
  address: string;
  addressDetail: string;
};

export type RegisterPayload = {
  username: string;
  password: string;
  name: string | null;
  email: string | null;
  business_name: string;
  business_type: string;
  address: string;
  address_detail: string | null;
};

type RegistrationApi = {
  register(payload: RegisterPayload): Promise<UserResponse>;
  login(payload: { username: string; password: string }): Promise<UserResponse>;
};

export class RegistrationCompletedLoginFailed extends Error {
  constructor(public readonly username: string) {
    super("회원가입은 완료되었지만 자동 로그인에 실패했습니다.");
    this.name = "RegistrationCompletedLoginFailed";
  }
}

function required(value: string, label: string): string {
  const normalized = value.trim();
  if (!normalized) throw new Error(`${label}을(를) 입력해주세요.`);
  return normalized;
}

function optional(value: string): string | null {
  const normalized = value.trim();
  return normalized || null;
}

export function buildRegisterPayload(fields: RegistrationFields): RegisterPayload {
  if (fields.password !== fields.passwordConfirm) {
    throw new Error("비밀번호가 일치하지 않습니다.");
  }
  const passwordBytes = new TextEncoder().encode(fields.password).byteLength;
  if (passwordBytes < 8 || passwordBytes > 72) {
    throw new Error("비밀번호는 UTF-8 기준 8~72바이트여야 합니다.");
  }

  return {
    username: required(fields.username, "사용자명").toLowerCase(),
    password: fields.password,
    name: optional(fields.name),
    email: optional(fields.email),
    business_name: required(fields.businessName, "가게명"),
    business_type: required(fields.businessType, "업종"),
    address: required(fields.address, "주소"),
    address_detail: optional(fields.addressDetail),
  };
}

export async function registerAndLogin(
  api: RegistrationApi,
  fields: RegistrationFields,
): Promise<UserResponse> {
  const payload = buildRegisterPayload(fields);
  await api.register(payload);
  try {
    return await api.login({ username: payload.username, password: payload.password });
  } catch {
    throw new RegistrationCompletedLoginFailed(payload.username);
  }
}

function errorCode(detail: unknown): string | null {
  if (typeof detail !== "object" || detail === null || !("code" in detail)) return null;
  return typeof detail.code === "string" ? detail.code : null;
}

export function authErrorMessage(error: unknown): string {
  if (error instanceof RegistrationCompletedLoginFailed) return error.message;
  if (error instanceof Error && !(error instanceof ApiError)) return error.message;
  if (!(error instanceof ApiError)) return "Backend에 연결할 수 없습니다.";

  const code = errorCode(error.detail);
  if (code === "duplicate_username") return "이미 사용 중인 사용자명입니다.";
  if (code === "duplicate_email") return "이미 사용 중인 이메일입니다.";
  if (code === "address_not_found") return "주소를 더 구체적으로 입력해주세요.";
  if (code === "geocoding_unavailable") return "주소 확인 서비스가 불안정합니다. 잠시 후 다시 시도해주세요.";
  if (error.statusCode === 401) return "사용자명 또는 비밀번호를 확인해주세요.";
  if (error.statusCode === 422) return "입력값을 다시 확인해주세요.";
  return "요청을 처리하지 못했습니다. 잠시 후 다시 시도해주세요.";
}
