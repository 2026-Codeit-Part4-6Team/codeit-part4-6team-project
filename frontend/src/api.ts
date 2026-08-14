import type { EstimatePayload, EstimateResponse, GeneratePayload } from "./contract";

export class ApiError extends Error {
  constructor(
    public readonly statusCode: number,
    public readonly detail: unknown,
  ) {
    super(`API request failed with status ${statusCode}`);
    this.name = "ApiError";
  }
}

export type UserResponse = {
  id: number;
  username: string;
  business_name?: string | null;
  credits?: number;
  daily_free_remaining?: number;
};

export type GenerationResponse = {
  generation_id: number;
  status: string;
  chatbot_type: "basic" | "consultant";
  result: Record<string, unknown> | null;
  usage: { plan: "free" | "paid"; credits_used: number };
};

export class ApiClient {
  constructor(
    private readonly baseUrl = "/api",
    private readonly fetcher: typeof fetch = fetch.bind(globalThis),
  ) {}

  private async request<T>(path: string, init: RequestInit): Promise<T> {
    const response = await this.fetcher(`${this.baseUrl}${path}`, {
      ...init,
      credentials: "include",
      headers: {
        "Content-Type": "application/json",
        ...init.headers,
      },
    });
    const text = await response.text();
    let body: unknown = {};
    if (text) {
      try {
        body = JSON.parse(text);
      } catch {
        body = "서버가 JSON이 아닌 오류 응답을 반환했습니다.";
      }
    }
    if (!response.ok) {
      const detail =
        typeof body === "object" && body !== null && "detail" in body
          ? (body as { detail: unknown }).detail
          : body;
      throw new ApiError(response.status, detail);
    }
    return body as T;
  }

  login(payload: { username: string; password: string }): Promise<UserResponse> {
    return this.request("/auth/login", {
      method: "POST",
      body: JSON.stringify(payload),
    });
  }

  me(): Promise<UserResponse> {
    return this.request("/users/me", { method: "GET" });
  }

  estimate(payload: EstimatePayload): Promise<EstimateResponse> {
    return this.request("/generate/estimate", {
      method: "POST",
      body: JSON.stringify(payload),
    });
  }

  generate(payload: GeneratePayload, idempotencyKey: string): Promise<GenerationResponse> {
    return this.request("/generate", {
      method: "POST",
      body: JSON.stringify(payload),
      headers: { "Idempotency-Key": idempotencyKey },
    });
  }
}
