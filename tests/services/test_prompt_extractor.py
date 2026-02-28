from __future__ import annotations

from pathlib import Path

import pytest

from app.services.prompt_extractor import extract_generation_prompts


@pytest.mark.parametrize(
    ("filename", "expected_positive", "expected_negative"),
    [
        (
            "00009.png",
            ["old male", "holding cat", "masterpiece", "best quality"],
            ["worst quality", "bad quality", "bad anatomy", "bad hands"],
        ),
        (
            "00010.avif",
            ["old male", "holding cat", "masterpiece", "best quality"],
            ["worst quality", "bad quality", "bad anatomy", "bad hands"],
        ),
        (
            "00025.avif",
            ["mountain", "scenery", "masterpiece", "best quality"],
            [],
        ),
        (
            "00027.avif",
            ["knight", "solo", "masterpiece"],
            ["bad anatomy", "bad hands"],
        ),
        (
            "00029.avif",
            ["old male", "solo"],
            ["worst quality"],
        ),
    ],
)
def test_extract_generation_prompts_from_test_assets(
    filename: str,
    expected_positive: list[str],
    expected_negative: list[str],
):
    result = extract_generation_prompts(Path("tests/resources/images_with_prompt/dir1") / filename)

    assert result is not None
    assert result.positive == expected_positive
    assert result.negative == expected_negative
