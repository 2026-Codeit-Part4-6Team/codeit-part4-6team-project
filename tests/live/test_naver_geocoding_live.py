import asyncio
import os
from pathlib import Path

import pytest
from dotenv import load_dotenv

from backend.clients.geocoding_client import NaverGeocodingClient


@pytest.mark.live
def test_naver_geocoding_contract_against_real_provider():
    """실제 NCP endpoint·헤더·응답 계약으로 주소와 좌표를 조회합니다."""
    load_dotenv(Path(__file__).parents[2] / ".env", override=False)
    api_key_id = os.getenv("NAVER_MAPS_API_KEY_ID")
    api_key = os.getenv("NAVER_MAPS_API_KEY")
    if not api_key_id or not api_key:
        pytest.skip("NAVER_MAPS_API_KEY_ID와 NAVER_MAPS_API_KEY가 필요합니다.")

    result = asyncio.run(
        NaverGeocodingClient(api_key_id=api_key_id, api_key=api_key).geocode(
            "분당구 불정로 6"
        )
    )

    assert result.road_address
    assert 33 <= result.lat <= 39
    assert 124 <= result.lng <= 132
