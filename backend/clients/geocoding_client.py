from dataclasses import dataclass
from typing import Protocol, runtime_checkable

import httpx

from backend.config import settings

NAVER_GEOCODING_BASE_URL = "https://maps.apigw.ntruss.com"
NAVER_GEOCODING_PATH = "/map-geocode/v2/geocode"


@dataclass(frozen=True)
class GeocodingResult:
    """주소 검색으로 확인한 도로명 주소와 좌표입니다."""

    road_address: str
    lat: float
    lng: float


class GeocodingNotFound(Exception):
    """정상적인 주소 검색 결과가 없을 때 발생합니다."""


class GeocodingProviderError(Exception):
    """지오코딩 제공자 호출 또는 응답 해석에 실패할 때 발생합니다."""


@runtime_checkable
class GeocodingClient(Protocol):
    """서비스가 지오코딩 구현을 호출하는 공통 경계입니다."""

    async def geocode(self, address: str) -> GeocodingResult:
        """입력 주소를 정규화한 주소와 좌표로 변환합니다."""
        ...


class NaverGeocodingClient:
    """NAVER Maps Geocoding API를 호출하는 클라이언트입니다."""

    def __init__(
        self,
        api_key_id: str,
        api_key: str,
        *,
        timeout_seconds: float = 10.0,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self._headers = {
            "Accept": "application/json",
            "x-ncp-apigw-api-key-id": api_key_id,
            "x-ncp-apigw-api-key": api_key,
        }
        self._timeout_seconds = timeout_seconds
        self._transport = transport

    async def geocode(self, address: str) -> GeocodingResult:
        """NAVER API의 첫 번째 검색 결과를 서비스 좌표로 변환합니다."""
        try:
            async with httpx.AsyncClient(
                base_url=NAVER_GEOCODING_BASE_URL,
                headers=self._headers,
                timeout=self._timeout_seconds,
                transport=self._transport,
            ) as client:
                response = await client.get(NAVER_GEOCODING_PATH, params={"query": address})
                response.raise_for_status()
            payload = response.json()
        except (httpx.HTTPError, ValueError) as error:
            raise GeocodingProviderError("지오코딩 제공자 호출에 실패했습니다.") from error

        try:
            if payload.get("status") != "OK":
                raise GeocodingProviderError("지오코딩 제공자가 오류 상태를 반환했습니다.")
            addresses = payload["addresses"]
            if not addresses:
                raise GeocodingNotFound(address)
            first = addresses[0]
            road_address = first.get("roadAddress") or first["jibunAddress"]
            return GeocodingResult(
                road_address=road_address,
                lat=float(first["y"]),
                lng=float(first["x"]),
            )
        except GeocodingNotFound:
            raise
        except GeocodingProviderError:
            raise
        except (AttributeError, KeyError, TypeError, ValueError) as error:
            raise GeocodingProviderError("지오코딩 응답 형식이 올바르지 않습니다.") from error


def get_geocoding_client() -> GeocodingClient:
    """환경변수 인증 정보로 NAVER 지오코딩 클라이언트를 제공합니다."""
    return NaverGeocodingClient(
        api_key_id=settings.naver_maps_api_key_id,
        api_key=settings.naver_maps_api_key,
    )
