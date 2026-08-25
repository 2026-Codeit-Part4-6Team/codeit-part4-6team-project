type PlaceholderPageProps = {
  title: string;
  description: string;
  onBack: () => void;
};

export function PlaceholderPage({ title, description, onBack }: PlaceholderPageProps) {
  return (
    <section className="placeholder-page">
      <span className="greeting-mark" aria-hidden="true" />
      <p className="kicker">D5 NAVIGATION READY</p>
      <h1>{title}</h1>
      <p>{description}</p>
      <button type="button" className="primary" onClick={onBack}>대시보드로 돌아가기</button>
    </section>
  );
}
