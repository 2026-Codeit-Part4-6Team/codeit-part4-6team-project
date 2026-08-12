import asyncio

import httpx
import pytest

from backend.clients.geocoding_client import (
    GeocodingNotFound,
    GeocodingProviderError,
    NaverGeocodingClient,
)


def test_geocode_uses_naver_contract_and_returns_first_address():
    """네이버 계약으로 요청하고 첫 번째 주소의 좌표를 반환합니다."""
    captured_request: httpx.Request | None = None

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal captured_request
        captured_request = request
        return httpx.Response(
            200,
            json={
                "status": "OK",
                "addresses": [
                    {
                        "roadAddress": "서울특별시 강남구 테헤란로 1",
                        "jibunAddress": "서울특별시 강남구 역삼동 1",
                        "x": "127.0276",
                        "y": "37.4979",
                    }
                ],
            },
        )

    client = NaverGeocodingClient(
        api_key_id="client-id",
        api_key="client-secret",
        transport=httpx.MockTransport(handler),
    )

    result = asyncio.run(client.geocode("서울 강남구 테헤란로 1"))

    assert result.road_address == "서울특별시 강남구 테헤란로 1"
    assert result.lat == pytest.approx(37.4979)
    assert result.lng == pytest.approx(127.0276)
    assert captured_request is not None
    assert captured_request.url.path == "/map-geocode/v2/geocode"
    assert captured_request.url.params["query"] == "서울 강남구 테헤란로 1"
    assert captured_request.headers["x-ncp-apigw-api-key-id"] == "client-id"
    assert captured_request.headers["x-ncp-apigw-api-key"] == "client-secret"


def test_geocode_uses_jibun_address_when_road_address_is_empty():
    """도로명 주소가 없으면 지번 주소를 저장 주소로 사용합니다."""

    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "status": "OK",
                "addresses": [
                    {
                        "roadAddress": "",
                        "jibunAddress": "서울특별시 강남구 역삼동 1",
                        "x": "127.0",
                        "y": "37.5",
                    }
                ],
            },
        )

    client = NaverGeocodingClient(
        api_key_id="id",
        api_key="secret",
        transport=httpx.MockTransport(handler),
    )

    result = asyncio.run(client.geocode("역삼동 1"))

    assert result.road_address == "서울특별시 강남구 역삼동 1"


def test_geocode_raises_not_found_for_empty_addresses():
    """정상 응답에 검색 결과가 없으면 사용자 입력 오류로 구분합니다."""

    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"status": "OK", "addresses": []})

    client = NaverGeocodingClient(
        api_key_id="id",
        api_key="secret",
        transport=httpx.MockTransport(handler),
    )

    with pytest.raises(GeocodingNotFound):
        asyncio.run(client.geocode("존재하지 않는 주소"))


@pytest.mark.parametrize("failure", ["timeout", "http", "invalid_json", "invalid_payload"])
def test_geocode_wraps_provider_failures(failure: str):
    """통신 및 제공자 응답 오류를 하나의 외부 장애로 변환합니다."""

    def handler(request: httpx.Request) -> httpx.Response:
        if failure == "timeout":
            raise httpx.ReadTimeout("timeout", request=request)
        if failure == "http":
            return httpx.Response(500, json={"error": "server error"})
        if failure == "invalid_json":
            return httpx.Response(200, content=b"not-json")
        return httpx.Response(
            200,
            json={"status": "OK", "addresses": [{"roadAddress": "주소", "x": "x", "y": "y"}]},
        )

    client = NaverGeocodingClient(
        api_key_id="id",
        api_key="secret",
        transport=httpx.MockTransport(handler),
    )

    with pytest.raises(GeocodingProviderError):
        asyncio.run(client.geocode("서울"))


def test_geocode_rejects_provider_coordinates_outside_valid_ranges():
    """제공자가 반환한 범위 밖 좌표는 외부 장애로 처리합니다."""

    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "status": "OK",
                "addresses": [{"roadAddress": "주소", "x": "181", "y": "91"}],
            },
        )

    client = NaverGeocodingClient(
        api_key_id="id",
        api_key="secret",
        transport=httpx.MockTransport(handler),
    )

    with pytest.raises(GeocodingProviderError):
        asyncio.run(client.geocode("서울"))
