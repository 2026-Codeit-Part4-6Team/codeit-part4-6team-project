import { useEffect, useRef, useState } from "react";

import type { GeocodePreviewResponse } from "../api";

type NaverMapInstance = {
  setSize: (size: NaverSize) => void;
  destroy?: () => void;
};

type NaverSize = { width: number; height: number };

type NaverMapsApi = {
  maps: {
    Map: new (element: HTMLElement, options: { center: NaverLatLng; zoom: number }) => NaverMapInstance;
    LatLng: new (lat: number, lng: number) => NaverLatLng;
    Marker: new (options: { position: NaverLatLng; map: NaverMapInstance }) => NaverMarker;
    Size: new (width: number, height: number) => NaverSize;
  };
};

type NaverLatLng = object;
type NaverMarker = { setMap: (map: NaverMapInstance | null) => void };

declare global {
  interface Window {
    naver?: NaverMapsApi;
  }
}

let naverSdkPromise: Promise<void> | null = null;

function loadNaverMaps(clientId: string): Promise<void> {
  if (typeof window === "undefined") return Promise.reject(new Error("브라우저에서만 지도를 불러올 수 있습니다."));
  if (window.naver?.maps) return Promise.resolve();
  if (naverSdkPromise) return naverSdkPromise;

  naverSdkPromise = new Promise<void>((resolve, reject) => {
    const existing = document.querySelector<HTMLScriptElement>("script[data-naver-maps-sdk]");
    const script = existing ?? document.createElement("script");
    script.dataset.naverMapsSdk = "true";
    script.src = `https://oapi.map.naver.com/openapi/v3/maps.js?ncpKeyId=${encodeURIComponent(clientId)}`;
    script.async = true;
    script.onload = () => window.naver?.maps ? resolve() : reject(new Error("네이버 지도 SDK를 초기화하지 못했습니다."));
    script.onerror = () => reject(new Error("네이버 지도 SDK를 불러오지 못했습니다."));
    if (!existing) document.head.appendChild(script);
  });
  return naverSdkPromise;
}

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
  const mapElement = useRef<HTMLDivElement>(null);
  const mapRef = useRef<NaverMapInstance | null>(null);
  const markerRef = useRef<NaverMarker | null>(null);
  const [mapError, setMapError] = useState<string | null>(null);
  const clientId = import.meta.env.VITE_NAVER_MAPS_CLIENT_ID?.trim();

  useEffect(() => {
    if (!clientId || !mapElement.current) {
      setMapError("지도 Client ID가 설정되지 않아 좌표 정보만 표시합니다.");
      return;
    }

    let cancelled = false;
    const element = mapElement.current;
    let observer: ResizeObserver | null = null;
    void loadNaverMaps(clientId)
      .then(() => {
        if (cancelled || !element || !window.naver) return;
        const { maps } = window.naver;
        const center = new maps.LatLng(preview.lat, preview.lng);
        const map = new maps.Map(element, { center, zoom: 16 });
        const marker = new maps.Marker({ position: center, map });
        mapRef.current = map;
        markerRef.current = marker;

        const resize = () => map.setSize(new maps.Size(element.clientWidth, element.clientHeight));
        observer = new ResizeObserver(resize);
        observer.observe(element);
        resize();
      })
      .catch((error: unknown) => {
        if (!cancelled) setMapError(error instanceof Error ? error.message : "지도를 불러오지 못했습니다.");
      });

    return () => {
      cancelled = true;
      observer?.disconnect();
      markerRef.current?.setMap(null);
      mapRef.current?.destroy?.();
      markerRef.current = null;
      mapRef.current = null;
    };
  }, [clientId, preview.lat, preview.lng]);

  return (
    <div className="map-preview" aria-label="주소 지도 미리보기">
      <div className="map-preview-heading">
        <div>
          <strong>{heading}</strong>
          <span>{preview.road_address}</span>
        </div>
        <span className="map-preview-badge">주소 확인됨</span>
      </div>
      <div ref={mapElement} className="naver-map-container" aria-label={`${preview.road_address} 네이버 지도`} />
      {mapError && <p className="map-preview-message map-preview-message--error">{mapError}</p>}
      <small>{caption}</small>
    </div>
  );
}
