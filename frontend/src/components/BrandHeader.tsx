import { BrandMark } from "./BrandMark";

type BrandHeaderProps = {
  subtitle: string;
  onClick?: () => void;
};

export function BrandHeader({ subtitle, onClick }: BrandHeaderProps) {
  return (
    <header className="brand-header">
      <div className="brand-title-row">
        <BrandMark onClick={onClick} />
      </div>
      <p>{subtitle}</p>
    </header>
  );
}
