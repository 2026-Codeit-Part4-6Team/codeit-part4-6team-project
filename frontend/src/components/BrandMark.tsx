type BrandMarkProps = { onClick?: () => void };

export function BrandMark({ onClick }: BrandMarkProps) {
  const content = (
    <span className="brand-mark" aria-label="매출부스터">
      <span className="brand-mark-word">
        <strong>매출부스터</strong>
      </span>
    </span>
  );

  if (!onClick) return content;
  return (
    <button type="button" className="brand-mark-button" aria-label="매출부스터 메인으로 이동" onClick={onClick}>
      {content}
    </button>
  );
}
