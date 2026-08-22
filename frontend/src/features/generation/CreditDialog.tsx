import type { EstimateResponse } from "../../contract";

type CreditDialogProps = {
  estimate: EstimateResponse;
  onConfirm: () => void;
  onCancel: () => void;
  disabled?: boolean;
};

export function CreditDialog({
  estimate,
  onConfirm,
  onCancel,
  disabled = false,
}: CreditDialogProps) {
  if (!estimate.requires_confirmation) {
    return null;
  }

  return (
    <section className="credit-dialog" role="dialog" aria-modal="true">
      <div className="credit-dialog-header">
        <div className="credit-dialog-icon" aria-hidden="true">✦</div>
        <div>
          <p className="kicker">CREDIT CONFIRMATION</p>
          <h2>Credit 사용에 동의해 주세요</h2>
          <p className="credit-dialog-subtitle">생성을 시작하면 아래 예상량만큼 Credit이 차감됩니다.</p>
        </div>
      </div>
      <dl className="credit-summary">
        <div>
          <dt>예상 사용량</dt>
          <dd>{estimate.estimated_credits} Credit</dd>
        </div>
        <div>
          <dt>현재 잔액</dt>
          <dd>{estimate.current_credits ?? 0} Credit</dd>
        </div>
        <div>
          <dt>사용 후 잔액</dt>
          <dd>{estimate.credits_after ?? 0} Credit</dd>
        </div>
      </dl>
      <div className="dialog-actions">
        <button type="button" className="dialog-button dialog-button-secondary" onClick={onCancel} disabled={disabled}>
          <span aria-hidden="true">←</span>
          취소
        </button>
        <button type="button" className="dialog-button dialog-button-primary" onClick={onConfirm} disabled={disabled}>
          <span aria-hidden="true">✓</span>
          <span>{disabled ? "생성 준비 중…" : "동의하고 생성"}</span>
        </button>
      </div>
    </section>
  );
}
