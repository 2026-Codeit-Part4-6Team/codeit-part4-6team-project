type CryptoSource = Pick<Crypto, "getRandomValues"> &
  Partial<Pick<Crypto, "randomUUID">>;

function formatUuid(bytes: Uint8Array): string {
  const hex = Array.from(bytes, (byte) => byte.toString(16).padStart(2, "0")).join("");
  return `${hex.slice(0, 8)}-${hex.slice(8, 12)}-${hex.slice(12, 16)}-${hex.slice(16, 20)}-${hex.slice(20)}`;
}

/**
 * HTTP 환경에서도 사용할 수 있는 멱등 키를 생성합니다.
 * randomUUID()를 사용할 수 없는 일반 HTTP origin에서는 getRandomValues로
 * RFC 4122 v4 UUID를 만들어 결제·생성 재요청 키로 사용합니다.
 */
export function createIdempotencyKey(
  cryptoSource: CryptoSource = globalThis.crypto,
): string {
  if (typeof cryptoSource.randomUUID === "function") {
    return cryptoSource.randomUUID();
  }

  const bytes = new Uint8Array(16);
  cryptoSource.getRandomValues(bytes);
  bytes[6] = (bytes[6] & 0x0f) | 0x40;
  bytes[8] = (bytes[8] & 0x3f) | 0x80;
  return formatUuid(bytes);
}
