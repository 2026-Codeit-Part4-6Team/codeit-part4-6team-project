import { type FormEvent, useState } from "react";

import { type ApiClient, type UserResponse } from "../api";
import {
  authErrorMessage,
  registerAndLogin,
  RegistrationCompletedLoginFailed,
  type RegistrationFields,
} from "../auth";
import { BrandHeader } from "./BrandHeader";

const emptyRegistration: RegistrationFields = {
  username: "",
  password: "",
  passwordConfirm: "",
  name: "",
  email: "",
  businessName: "",
  businessType: "",
  address: "",
  addressDetail: "",
};

type AuthScreenProps = {
  api: ApiClient;
  onAuthenticated: (user: UserResponse) => void;
};

export function AuthScreen({ api, onAuthenticated }: AuthScreenProps) {
  const [mode, setMode] = useState<"login" | "register">("login");
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [registration, setRegistration] = useState<RegistrationFields>(emptyRegistration);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  function switchMode(nextMode: "login" | "register") {
    setMode(nextMode);
    setError(null);
  }

  function updateRegistration(key: keyof RegistrationFields, value: string) {
    setRegistration((current) => ({ ...current, [key]: value }));
  }

  async function submitLogin(event: FormEvent) {
    event.preventDefault();
    setBusy(true);
    setError(null);
    try {
      onAuthenticated(await api.login({ username, password }));
      setPassword("");
    } catch (caught) {
      setError(authErrorMessage(caught));
    } finally {
      setBusy(false);
    }
  }

  async function submitRegistration(event: FormEvent) {
    event.preventDefault();
    setBusy(true);
    setError(null);
    try {
      onAuthenticated(await registerAndLogin(api, registration));
      setRegistration(emptyRegistration);
    } catch (caught) {
      if (caught instanceof RegistrationCompletedLoginFailed) {
        setUsername(caught.username);
        setPassword("");
        setMode("login");
      }
      setError(authErrorMessage(caught));
    } finally {
      setBusy(false);
    }
  }

  return (
    <main className={`auth-shell auth-shell--${mode}`}>
      {mode === "login" ? (
        <header className="auth-login-brand">
          <img
            className="auth-brand-logo"
            src="/assets/brand/salesbooster-logo.png"
            alt="매출부스터 AI"
          />
          <p>소상공인을 위한 AI 마케팅 어시스턴트</p>
        </header>
      ) : (
        <BrandHeader subtitle="새 계정 만들기" />
      )}

      {mode === "login" ? (
        <>
          <div className="auth-login-stage">
            <figure className="auth-mascot auth-mascot--copyni">
              <img src="/assets/mascots/copyni.png" alt="광고 제작 파트너 카피니" />
              <figcaption>카피니</figcaption>
            </figure>
            <section className="auth-card" aria-labelledby="login-title">
              <h1 id="login-title" className="sr-only">로그인</h1>
              <form className="auth-form" onSubmit={submitLogin}>
                <label>
                  사용자명
                  <input
                    name="username"
                    autoComplete="username"
                    value={username}
                    onChange={(event) => setUsername(event.target.value)}
                    minLength={3}
                    placeholder="사용자명을 입력해 주세요"
                    required
                  />
                </label>
                <label>
                  비밀번호
                  <input
                    name="password"
                    type="password"
                    autoComplete="current-password"
                    value={password}
                    onChange={(event) => setPassword(event.target.value)}
                    minLength={8}
                    required
                  />
                </label>
                {error && <div className="error-banner" role="alert">{error}</div>}
                <button className="primary auth-submit" disabled={busy}>
                  {busy ? "확인 중…" : "로그인"}
                </button>
              </form>
            </section>
            <figure className="auth-mascot auth-mascot--bunseoki">
              <img src="/assets/mascots/bunseoki.png" alt="상권 분석 파트너 분석이" />
              <figcaption>분석이</figcaption>
            </figure>
          </div>
          <p className="auth-switch-copy">
            계정이 없으신가요?
            <button type="button" onClick={() => switchMode("register")}>회원가입</button>
          </p>
        </>
      ) : (
        <section className="auth-card auth-card--register" aria-labelledby="register-title">
          <h1 id="register-title" className="sr-only">회원가입</h1>
          <form className="auth-form registration-form" onSubmit={submitRegistration}>
            <fieldset>
              <legend>계정</legend>
              <label>
                사용자명
                <input
                  name="register-username"
                  autoComplete="username"
                  value={registration.username}
                  onChange={(event) => updateRegistration("username", event.target.value)}
                  minLength={3}
                  required
                />
              </label>
              <label>
                비밀번호
                <input
                  name="new-password"
                  type="password"
                  autoComplete="new-password"
                  value={registration.password}
                  onChange={(event) => updateRegistration("password", event.target.value)}
                  minLength={8}
                  required
                />
              </label>
              <label>
                비밀번호 확인
                <input
                  name="password-confirm"
                  type="password"
                  autoComplete="new-password"
                  value={registration.passwordConfirm}
                  onChange={(event) => updateRegistration("passwordConfirm", event.target.value)}
                  minLength={8}
                  required
                />
              </label>
            </fieldset>
            <fieldset>
              <legend>가게</legend>
              <label>
                가게명
                <input
                  name="business-name"
                  value={registration.businessName}
                  onChange={(event) => updateRegistration("businessName", event.target.value)}
                  required
                />
              </label>
              <label>
                업종
                <input
                  name="business-type"
                  value={registration.businessType}
                  onChange={(event) => updateRegistration("businessType", event.target.value)}
                  placeholder="예: 카페, 음식점, 미용실"
                  required
                />
              </label>
            </fieldset>
            <fieldset>
              <legend>위치</legend>
              <label>
                주소
                <input
                  name="address"
                  value={registration.address}
                  onChange={(event) => updateRegistration("address", event.target.value)}
                  placeholder="예: 서울 강남구 테헤란로 1"
                  required
                />
              </label>
              <label>
                상세주소 <small>선택</small>
                <input
                  name="address-detail"
                  value={registration.addressDetail}
                  onChange={(event) => updateRegistration("addressDetail", event.target.value)}
                />
              </label>
            </fieldset>
            <fieldset>
              <legend>선택 정보</legend>
              <label>
                이름 <small>선택</small>
                <input
                  name="name"
                  autoComplete="name"
                  value={registration.name}
                  onChange={(event) => updateRegistration("name", event.target.value)}
                />
              </label>
              <label>
                이메일 <small>선택</small>
                <input
                  name="email"
                  type="email"
                  autoComplete="email"
                  value={registration.email}
                  onChange={(event) => updateRegistration("email", event.target.value)}
                />
              </label>
            </fieldset>
            {error && <div className="error-banner" role="alert">{error}</div>}
            <button className="primary auth-submit" disabled={busy}>
              {busy ? "가입 중…" : "회원가입"}
            </button>
          </form>
          <p className="auth-switch-copy auth-switch-copy--inside">
            이미 계정이 있으신가요?
            <button type="button" onClick={() => switchMode("login")}>로그인</button>
          </p>
        </section>
      )}
    </main>
  );
}
