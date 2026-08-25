import { useState } from "react";

import type { ApiClient, UserResponse } from "../api";
import { AddressMapPreview } from "./AddressMapPreview";

type StoreProfilePageProps = {
  api: ApiClient;
  user: UserResponse;
  onBack: () => void;
  onSaved?: (user: UserResponse) => void;
};

export function StoreProfilePage({ api, user, onBack, onSaved }: StoreProfilePageProps) {
  const [businessName, setBusinessName] = useState(user.business_name ?? "");
  const [businessType, setBusinessType] = useState(user.business_type ?? "");
  const [addressDetail, setAddressDetail] = useState(user.address_detail ?? "");
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function save() {
    if (!businessName.trim() || !businessType.trim()) {
      setError("가게명과 업종을 입력해 주세요.");
      return;
    }
    setSaving(true);
    setError(null);
    setMessage(null);
    try {
      const updated = await api.updateStoreProfile({
        business_name: businessName.trim(),
        business_type: businessType.trim(),
        address_detail: addressDetail.trim() || null,
      });
      onSaved?.(updated);
      setMessage("가게 정보가 저장되었습니다.");
    } catch {
      setError("가게 정보를 저장하지 못했습니다. 잠시 후 다시 시도해 주세요.");
    } finally {
      setSaving(false);
    }
  }

  return (
    <section className="account-page store-profile-page" aria-labelledby="store-profile-title">
      <button type="button" className="back-link" onClick={onBack}>← 대시보드로 돌아가기</button>
      <div className="page-heading">
        <p className="kicker">MY STORE</p>
        <h1 id="store-profile-title">가게 정보 수정</h1>
        <p>광고 생성과 상권 분석에 사용할 가게 정보를 최신 상태로 유지하세요.</p>
      </div>
      <section className="card store-profile-card">
        <label>
          가게명
          <input value={businessName} onChange={(event) => setBusinessName(event.target.value)} />
        </label>
        <label>
          업종
          <input value={businessType} onChange={(event) => setBusinessType(event.target.value)} />
        </label>
        <label>
          주소
          <input value={user.road_address ?? user.address ?? "주소 미등록"} readOnly aria-readonly="true" />
          <small>주소 좌표와 상권 데이터의 기준이므로 현재는 회원가입 주소를 사용합니다.</small>
        </label>
        {user.lat !== null && user.lng !== null && (
          <AddressMapPreview
            preview={{
              query: user.address ?? user.road_address ?? "",
              road_address: user.road_address ?? user.address ?? "주소 미등록",
              lat: user.lat,
              lng: user.lng,
            }}
            heading="현재 상권 분석 기준 위치"
            caption="이 좌표를 기준으로 광고 생성과 상권 분석이 진행됩니다."
          />
        )}
        <label>
          상세 주소
          <input value={addressDetail} onChange={(event) => setAddressDetail(event.target.value)} />
        </label>
        {error && <p className="form-error" role="alert">{error}</p>}
        {message && <p className="saved-note" role="status">{message}</p>}
        <button type="button" className="primary" disabled={saving} onClick={() => void save()}>
          {saving ? "저장 중…" : "가게 정보 저장"}
        </button>
      </section>
    </section>
  );
}
