import pytest
from pydantic import ValidationError

from app.models.schemas import GenerateRequest


def test_generate_request_defaults():
    request = GenerateRequest(topic="A useful topic")
    assert request.provider == "gemini"
    assert request.aspect_ratio == "9:16"
    assert request.clip_duration == 4.0
    assert request.subtitle_color == "#FFFFFF"
    assert request.subtitle_format == "ass"
    assert request.gpu_backend == "auto"
    assert request.batch_count == 1


def test_batch_limit():
    with pytest.raises(ValidationError):
        GenerateRequest(topic="A useful topic", batch_count=5)


def test_subtitle_color_validation():
    with pytest.raises(ValidationError):
        GenerateRequest(topic="A useful topic", subtitle_color="white")
