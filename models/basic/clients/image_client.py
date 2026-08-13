from openai import OpenAI

_client = None


def _get_client():
    global _client
    if _client is None:
        _client = OpenAI()
    return _client


def generate_image(prompt: str) -> str:
    pass
