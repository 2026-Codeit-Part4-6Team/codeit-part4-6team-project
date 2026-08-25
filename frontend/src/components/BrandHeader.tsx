type BrandHeaderProps = {
  subtitle: string;
};

export function BrandHeader({ subtitle }: BrandHeaderProps) {
  return (
    <header className="brand-header">
      <div className="brand-title-row">
        <span className="brand-logo" aria-hidden="true">매출</span>
        <span className="brand-name">매출부스터</span>
      </div>
      <p>{subtitle}</p>
    </header>
  );
}
