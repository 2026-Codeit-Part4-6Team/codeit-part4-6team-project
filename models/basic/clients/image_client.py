from openai import OpenAI

_client = None


def _get_client():
    global _client
    if _client is None:
        _client = OpenAI()
    return _client


def generate_image(prompt: str) -> str:
    """프롬프트를 받아 이미지를 생성하고 base64 인코딩된 이미지 문자열을 반환한다.

    TODO: 실제 이미지 생성 API 연동 필요 (현재 미구현, pass).
    """
