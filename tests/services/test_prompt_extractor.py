from __future__ import annotations

from pathlib import Path

from app.services.prompt_extractor import extract_generation_prompts


def test_extract_generation_prompts_from_png_parameters_chunk():
    result = extract_generation_prompts(Path("tests/resources/images_with_prompt/dir1/00009.png"))

    assert result is not None
    assert result.positive == ["old male", "holding cat", "masterpiece", "best quality"]
    assert result.negative == ["worst quality", "bad quality", "bad anatomy", "bad hands"]


def test_extract_generation_prompts_from_avif_exif_user_comment():
    result = extract_generation_prompts(Path("tests/resources/images_with_prompt/dir1/00025.avif"))

    assert result is not None
    assert result.positive == ["mountain", "scenery", "masterpiece", "best quality"]
    assert result.negative == []
