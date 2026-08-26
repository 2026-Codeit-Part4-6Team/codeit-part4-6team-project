import type { UserResponse } from "./api";

export type AppRoute =
  | "dashboard"
  | "basic_chatbot"
  | "consultant_chatbot"
  | "mypage"
  | "billing"
  | "settings";

export type AppViewState = {
  user: UserResponse | null;
  route: AppRoute;
};

export function authenticatedState(user: UserResponse): AppViewState {
  return { user, route: "dashboard" };
}

export function navigate(state: AppViewState, route: AppRoute): AppViewState {
  return { ...state, route };
}

export function loggedOutState(): AppViewState {
  return { user: null, route: "dashboard" };
}
