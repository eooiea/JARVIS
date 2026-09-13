"""Unit tests for JARVIS Vision & Screen Perception Pipeline (TDD Red-Green)."""

import io
import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch
from PIL import Image

from jarvis.vision.capture import ScreenCapture
from jarvis.vision.file_input import load_image_file, load_pdf_file
from jarvis.vision.analyzer import VisionAnalyzer
from jarvis.vision.anchor import VisionAnchorFinder


# ==========================================
# 1. ScreenCapture Tests
# ==========================================
def test_screen_capture_full_screen():
    """ScreenCapture should capture full screen and return valid PNG bytes."""
    with patch("jarvis.vision.capture.mss.mss") as mock_mss_cls:
        mock_sct = MagicMock()
        mock_sct.monitors = [{"left": 0, "top": 0, "width": 1920, "height": 1080},
                             {"left": 0, "top": 0, "width": 1920, "height": 1080}]
        
        # Create a tiny 10x10 mock BGRA image buffer
        dummy_img = Image.new("RGB", (10, 10), color="blue")
        mock_sct_img = MagicMock()
        mock_sct_img.size = (10, 10)
        mock_sct_img.rgb = dummy_img.tobytes()
        mock_sct.grab.return_value = mock_sct_img
        mock_mss_cls.return_value.__enter__.return_value = mock_sct

        capturer = ScreenCapture()
        img_bytes = capturer.capture_full_screen()

        assert isinstance(img_bytes, bytes)
        assert len(img_bytes) > 0
        # Verify it can be loaded as Pillow image
        pil_img = Image.open(io.BytesIO(img_bytes))
        assert pil_img.format == "PNG"


def test_screen_capture_region():
    """ScreenCapture should capture specified bounding box region."""
    with patch("jarvis.vision.capture.mss.mss") as mock_mss_cls:
        mock_sct = MagicMock()
        dummy_img = Image.new("RGB", (50, 30), color="red")
        mock_sct_img = MagicMock()
        mock_sct_img.size = (50, 30)
        mock_sct_img.rgb = dummy_img.tobytes()
        mock_sct.grab.return_value = mock_sct_img
        mock_mss_cls.return_value.__enter__.return_value = mock_sct

        capturer = ScreenCapture()
        img_bytes = capturer.capture_region(x=100, y=200, width=50, height=30)

        assert isinstance(img_bytes, bytes)
        mock_sct.grab.assert_called_with({"left": 100, "top": 200, "width": 50, "height": 30})


# ==========================================
# 2. FileInput Tests
# ==========================================
def test_load_image_file(tmp_path: Path):
    """load_image_file should load image and detect correct MIME type."""
    test_img = tmp_path / "sample.png"
    img = Image.new("RGB", (20, 20), color="green")
    img.save(test_img, format="PNG")

    img_bytes, mime_type = load_image_file(test_img)
    assert isinstance(img_bytes, bytes)
    assert mime_type == "image/png"


def test_load_image_file_not_found():
    """load_image_file should raise FileNotFoundError for nonexistent file."""
    with pytest.raises(FileNotFoundError):
        load_image_file("nonexistent_image_123.png")


def test_load_pdf_file(tmp_path: Path):
    """load_pdf_file should load PDF and return bytes with application/pdf MIME."""
    test_pdf = tmp_path / "sample.pdf"
    test_pdf.write_bytes(b"%PDF-1.4 mock pdf content")

    pdf_bytes, mime_type = load_pdf_file(test_pdf)
    assert isinstance(pdf_bytes, bytes)
    assert mime_type == "application/pdf"


# ==========================================
# 3. VisionAnalyzer Tests
# ==========================================
def test_vision_analyzer_parses_json():
    """VisionAnalyzer should parse structured JSON from LLM multimodal response."""
    mock_provider = MagicMock()
    mock_provider.generate_with_image.return_value = """
    ```json
    {
        "title": "식대 영수증",
        "total_amount": 32000,
        "items": [
            {"name": "김치찌개", "amount": 9000, "qty": 2},
            {"name": "제육볶음", "amount": 14000, "qty": 1}
        ]
    }
    ```
    """
    analyzer = VisionAnalyzer(provider=mock_provider)
    result = analyzer.analyze_structured_data(image_bytes=b"dummy_bytes", prompt="영수증 분석")

    assert isinstance(result, dict)
    assert result["title"] == "식대 영수증"
    assert result["total_amount"] == 32000
    assert len(result["items"]) == 2


def test_vision_analyzer_invalid_json_raises_error():
    """VisionAnalyzer should raise ValueError when LLM response is not valid JSON."""
    mock_provider = MagicMock()
    mock_provider.generate_with_image.return_value = "이것은 유효하지 않은 일반 텍스트입니다."

    analyzer = VisionAnalyzer(provider=mock_provider)
    with pytest.raises(ValueError) as exc_info:
        analyzer.analyze_structured_data(image_bytes=b"dummy_bytes")
    assert "JSON 파싱 실패" in str(exc_info.value)


# ==========================================
# 4. VisionAnchorFinder Tests
# ==========================================
def test_vision_anchor_finder_returns_coordinates():
    """VisionAnchorFinder should extract (x, y) coordinates for target UI field."""
    mock_provider = MagicMock()
    mock_provider.generate_with_image.return_value = '{"x": 450, "y": 320, "found": true}'

    finder = VisionAnchorFinder(provider=mock_provider)
    coords = finder.find_anchor(image_bytes=b"dummy_bytes", target_label="이름 입력창")

    assert coords == (450, 320)


def test_vision_anchor_finder_not_found():
    """VisionAnchorFinder should return None when target field is not detected."""
    mock_provider = MagicMock()
    mock_provider.generate_with_image.return_value = '{"found": false}'

    finder = VisionAnchorFinder(provider=mock_provider)
    coords = finder.find_anchor(image_bytes=b"dummy_bytes", target_label="없는 버튼")

    assert coords is None
