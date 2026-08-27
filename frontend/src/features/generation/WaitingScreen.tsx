import { useEffect, useState } from "react";

import type { ChatbotType, Platform } from "../../contract";
import { getWaitingExamples } from "./waitingExamples";

const WAITING_EXAMPLE_ROTATION_INTERVAL_MS = 15_000;

type WaitingScreenProps = {
  copyText: string;
  chatbotType?: ChatbotType;
  platform?: Platform;
};

export function WaitingScreen({ copyText, chatbotType = "basic", platform = "instagram" }: WaitingScreenProps) {
  const examples = getWaitingExamples(chatbotType, platform);
  const [activeIndex, setActiveIndex] = useState(0);
  const activeExample = examples[activeIndex % examples.length];

  useEffect(() => {
    setActiveIndex(0);
  }, [chatbotType, platform]);

  useEffect(() => {
    const timer = window.setInterval(() => {
      setActiveIndex((current) => (current + 1) % examples.length);
    }, WAITING_EXAMPLE_ROTATION_INTERVAL_MS);
    return () => window.clearInterval(timer);
  }, [examples.length]);

  const counterLabel = chatbotType === "consultant"
    ? "전략 예시"
    : `${platform === "xbanner" ? "X-배너" : "Instagram"} 예시`;

  return (
    <section className="waiting-screen" aria-live="polite" aria-busy="true">
      <div className="waiting-orbit waiting-orbit--spinning" role="status" aria-label="생성 진행 중" />
      <p className="kicker">생성 중</p>
      <h2>{copyText}</h2>
      <p>잠시만 기다려 주세요. 결과가 준비되면 자동으로 보여드릴게요.</p>
      <div className="waiting-example" aria-label="생성 중 예시 미리보기">
        <div className="waiting-example-heading"><span className="waiting-example-label">예시 미리보기</span><span>{counterLabel} {activeIndex + 1}/{examples.length}</span></div>
        <div className={`waiting-example-card waiting-example-card--${activeExample.variant}`}>
          <img src={activeExample.mascotSrc} alt="" aria-hidden="true" />
          <div><span>{activeExample.label}</span><strong>{activeExample.title}</strong><p>{activeExample.body}</p></div>
        </div>
        <div className="waiting-example-dots" aria-hidden="true">{examples.map((example, index) => <span className={index === activeIndex ? "is-active" : ""} key={`${example.title}-${index}`} />)}</div>
      </div>
    </section>
  );
}
