import type { ChatbotType, Platform } from "../../contract";

export type WaitingExample = {
  variant: "strategy" | "instagram" | "xbanner";
  label: string;
  title: string;
  body: string;
  mascotSrc: string;
};

const consultantExamples: WaitingExample[] = [
  { variant: "strategy", label: "상권 전략", title: "점심 직장인 고객을 먼저 잡아볼게요", body: "주변 상권과 가게 강점을 비교해 실행 순서를 정리하고 있어요.", mascotSrc: "/assets/mascots/bunseoki.png" },
  { variant: "strategy", label: "프로모션 아이디어", title: "이번 주말 방문을 늘릴 방법을 찾고 있어요", body: "고객이 바로 이해할 수 있는 혜택과 홍보 타이밍을 제안할게요.", mascotSrc: "/assets/mascots/bunseoki.png" },
  { variant: "strategy", label: "차별화 포인트", title: "우리 가게만의 이유를 선명하게 만들어요", body: "경쟁 매장과 겹치지 않는 메시지와 행동 계획을 준비 중이에요.", mascotSrc: "/assets/mascots/bunseoki.png" },
];

const instagramExamples: WaitingExample[] = [
  { variant: "instagram", label: "Instagram 예시", title: "여름 신메뉴, 오늘부터 만나보세요", body: "가볍고 친근한 피드·릴스용 카피를 다듬고 있어요.", mascotSrc: "/assets/mascots/copyni.png" },
  { variant: "instagram", label: "Instagram 예시", title: "이번 주말, 카페에서 만나요", body: "20대 고객에게 자연스럽게 닿는 문장과 이미지를 준비 중이에요.", mascotSrc: "/assets/mascots/copyni.png" },
  { variant: "instagram", label: "Instagram 예시", title: "한 잔의 여유가 필요한 날", body: "가게의 분위기가 느껴지는 정사각형 콘텐츠를 만들고 있어요.", mascotSrc: "/assets/mascots/copyni.png" },
];

const xbannerExamples: WaitingExample[] = [
  { variant: "xbanner", label: "X-배너 예시", title: "우리 가게의 특별한 하루", body: "세로형 X-배너에 맞춰 상단 카피와 하단 가게 정보를 배치하고 있어요.", mascotSrc: "/assets/mascots/copyni.png" },
  { variant: "xbanner", label: "X-배너 예시", title: "지금, 가장 맛있는 순간", body: "멀리서도 읽히는 짧은 문구와 세로형 비주얼을 준비 중이에요.", mascotSrc: "/assets/mascots/copyni.png" },
  { variant: "xbanner", label: "X-배너 예시", title: "사장님의 정성을 한눈에", body: "입구와 매장 앞에서 잘 보이는 세로형 메시지를 다듬고 있어요.", mascotSrc: "/assets/mascots/copyni.png" },
];

export function getWaitingExamples(chatbotType: ChatbotType, platform: Platform): WaitingExample[] {
  if (chatbotType === "consultant") return consultantExamples;
  return platform === "xbanner" ? xbannerExamples : instagramExamples;
}
