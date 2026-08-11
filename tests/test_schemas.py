import pytest
from pydantic import ValidationError

from app.models.schemas import GenerateRequest


def test_generate_request_defaults():
    request = GenerateRequest(topic="A useful topic")
    assert request.provider == "gemini"
    assert request.aspect_ratio == "9:16"
    assert request.batch_count == 1


def test_batch_limit():
    with pytest.raises(ValidationError):
        GenerateRequest(topic="A useful topic", batch_count=5)
