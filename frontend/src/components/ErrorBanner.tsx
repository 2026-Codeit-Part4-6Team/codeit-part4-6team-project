import { ApiError } from "../api";

type ErrorBannerProps = {
  error: unknown;
  onBilling?: () => void;
};

function safeMessage(error: unknown): string {
  if (!(error instanceof ApiError)) {
    return "요청을 처리하지 못했습니다. 잠시 후 다시 시도해 주세요.";
  }
  if (error.statusCode === 402) {
    return "Credit이 부족합니다. 충전 정책을 확인해 주세요.";
  }
  if (error.statusCode === 409) {
    return "요청 상태가 변경되었습니다. 최신 상태를 다시 확인해 주세요.";
  }
  if (error.statusCode === 422) {
    return "입력값을 확인한 뒤 다시 시도해 주세요.";
  }
  if (error.statusCode === 429) {
    return "요청이 많습니다. 잠시 후 다시 시도해 주세요.";
  }
  if (error.statusCode >= 500) {
    return "서비스 연결이 불안정합니다. 잠시 후 다시 시도해 주세요.";
  }
  if (error.statusCode === 401) {
    return "로그인이 만료되었습니다. 다시 로그인해 주세요.";
  }
  return "요청을 처리하지 못했습니다. 잠시 후 다시 시도해 주세요.";
}

export function ErrorBanner({ error, onBilling }: ErrorBannerProps) {
  const billing = error instanceof ApiError && error.statusCode === 402;
  return (
    <div className="error-banner wide" role="alert">
      <p>{safeMessage(error)}</p>
      {billing && onBilling && (
        <button type="button" onClick={onBilling}>
          충전 화면으로 이동
        </button>
      )}
    </div>
  );
}
