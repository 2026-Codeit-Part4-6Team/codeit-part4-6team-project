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
      <p className="kicker">CREDIT CONFIRMATION</p>
      <h2>Credit 사용에 동의해 주세요</h2>
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
        <button type="button" className="secondary" onClick={onCancel} disabled={disabled}>
          취소
        </button>
        <button type="button" onClick={onConfirm} disabled={disabled}>
          동의하고 생성
        </button>
      </div>
    </section>
  );
}
