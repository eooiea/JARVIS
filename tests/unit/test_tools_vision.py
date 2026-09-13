"""Unit tests for JARVIS Vision & Batch Document Analysis Tools (TDD Red-Green)."""

import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch
from jarvis.tools.vision import analyze_document, batch_analyze_documents, capture_screen


def test_analyze_document_single(tmp_path: Path):
    """analyze_document should extract structured JSON from a single image file."""
    mock_provider = MagicMock()
    mock_provider.generate_with_image.return_value = '{"title": "식대", "amount": 10000}'

    test_img = tmp_path / "receipt.png"
    test_img.write_bytes(b"\x89PNG dummy")

    result = analyze_document(test_img, provider=mock_provider)
    assert isinstance(result, dict)
    assert result["title"] == "식대"
    assert result["amount"] == 10000


def test_batch_analyze_documents(tmp_path: Path):
    """batch_analyze_documents should iterate over multiple files and return aggregated list of rows."""
    mock_provider = MagicMock()
    # Return different mock results for sequential calls
    mock_provider.generate_with_image.side_effect = [
        '{"상호명": "스타벅스", "금액": 6500, "일자": "2026-09-01"}',
        '{"상호명": "맥도날드", "금액": 9200, "일자": "2026-09-02"}',
    ]

    img1 = tmp_path / "receipt1.jpg"
    img2 = tmp_path / "receipt2.jpg"
    img1.write_bytes(b"\xFF\xD8 dummy1")
    img2.write_bytes(b"\xFF\xD8 dummy2")

    results = batch_analyze_documents([img1, img2], provider=mock_provider)

    assert isinstance(results, list)
    assert len(results) == 2
    assert results[0]["상호명"] == "스타벅스"
    assert results[0]["금액"] == 6500
    assert results[1]["상호명"] == "맥도날드"
    assert results[1]["금액"] == 9200
