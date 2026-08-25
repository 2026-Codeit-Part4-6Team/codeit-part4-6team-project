import type { GeocodePreviewResponse } from "../api";

type AddressMapPreviewProps = {
  preview: GeocodePreviewResponse;
  heading?: string;
  caption?: string;
};

export function AddressMapPreview({
  preview,
  heading = "이 위치로 가게를 등록할까요?",
  caption = "가입을 완료하면 이 좌표가 상권 분석 기준점으로 저장됩니다.",
}: AddressMapPreviewProps) {
  const delta = 0.004;
  const bbox = [
    preview.lng - delta,
    preview.lat - delta,
    preview.lng + delta,
    preview.lat + delta,
  ].join(",");
  const mapUrl = `https://www.openstreetmap.org/export/embed.html?bbox=${bbox}&layer=mapnik&marker=${preview.lat},${preview.lng}`;

  return (
    <div className="map-preview" aria-label="주소 지도 미리보기">
      <div className="map-preview-heading">
        <div>
          <strong>{heading}</strong>
          <span>{preview.road_address}</span>
        </div>
        <span className="map-preview-badge">주소 확인됨</span>
      </div>
      <iframe
        title={`${preview.road_address} 지도`}
        src={mapUrl}
        loading="lazy"
        referrerPolicy="no-referrer"
      />
      <small>{caption}</small>
    </div>
  );
}
