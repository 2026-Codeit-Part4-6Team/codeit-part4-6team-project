type WaitingScreenProps = {
  copyText: string;
};

export function WaitingScreen({ copyText }: WaitingScreenProps) {
  return (
    <section className="waiting-screen" aria-live="polite" aria-busy="true">
      <div className="waiting-orbit" aria-hidden="true" />
      <p className="kicker">생성 중</p>
      <h2>{copyText}</h2>
      <p>잠시만 기다려 주세요. 결과가 준비되면 자동으로 보여드릴게요.</p>
    </section>
  );
}
