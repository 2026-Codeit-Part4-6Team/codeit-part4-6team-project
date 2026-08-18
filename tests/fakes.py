from backend.clients.geocoding_client import GeocodingResult


class SuccessfulGeocodingClient:
    """외부 호출 없이 고정된 정상 지오코딩 결과를 반환합니다."""

    async def geocode(self, address: str) -> GeocodingResult:
        """입력 주소와 서울 기본 좌표를 반환합니다."""
        return GeocodingResult(road_address=address, lat=37.4979, lng=127.0276)
