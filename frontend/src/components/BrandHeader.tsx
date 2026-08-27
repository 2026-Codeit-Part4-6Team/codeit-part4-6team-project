import { BrandMark } from "./BrandMark";

type BrandHeaderProps = {
  subtitle: string;
};

export function BrandHeader({ subtitle }: BrandHeaderProps) {
  return (
    <header className="brand-header">
      <div className="brand-title-row">
        <BrandMark />
      </div>
      <p>{subtitle}</p>
    </header>
  );
}
