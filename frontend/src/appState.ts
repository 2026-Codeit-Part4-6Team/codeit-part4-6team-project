import type { UserResponse } from "./api";

export type AppRoute =
  | "dashboard"
  | "basic_chatbot"
  | "consultant_chatbot"
  | "mypage"
  | "billing"
  | "settings"
  | "store_settings";

export type AppViewState = {
  user: UserResponse | null;
  route: AppRoute;
  generationPrefill?: GenerationPrefill;
};

export type GenerationPrefill = {
  source_gen_id: number;
  question: string;
  purpose: string;
};

export function authenticatedState(user: UserResponse): AppViewState {
  return { user, route: "dashboard" };
}

export function navigate(state: AppViewState, route: AppRoute): AppViewState {
  return { user: state.user, route };
}

export function startBasicFromStrategy(
  state: AppViewState,
  sourceGenId: number,
  purpose = "",
): AppViewState {
  return {
    ...state,
    route: "basic_chatbot",
    generationPrefill: {
      source_gen_id: sourceGenId,
      question: "이 전략으로 광고 문구를 만들어줘",
      purpose,
    },
  };
}

export function loggedOutState(): AppViewState {
  return { user: null, route: "dashboard" };
}
