"""File loaders for local image and PDF inputs."""

from pathlib import Path
from typing import Tuple
from jarvis.utils.logger import get_logger

logger = get_logger("vision.file_input")


def load_image_file(file_path: Path | str) -> Tuple[bytes, str]:
    """Load local image file and determine MIME type."""
    path = Path(file_path).resolve()
    if not path.exists():
        raise FileNotFoundError(f"[이미지 파일을 찾을 수 없습니다: {path}]")

    suffix = path.suffix.lower()
    mime_map = {
        ".png": "image/png",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".webp": "image/webp",
        ".bmp": "image/bmp",
    }
    mime_type = mime_map.get(suffix, "image/png")
    image_bytes = path.read_bytes()
    logger.info(f"Loaded image: {path.name} ({len(image_bytes)} bytes, {mime_type})")
    return image_bytes, mime_type


def load_pdf_file(file_path: Path | str) -> Tuple[bytes, str]:
    """Load local PDF file and return bytes with application/pdf MIME."""
    path = Path(file_path).resolve()
    if not path.exists():
        raise FileNotFoundError(f"[PDF 파일을 찾을 수 없습니다: {path}]")

    if path.suffix.lower() != ".pdf":
        raise ValueError(f"[올바른 PDF 파일이 아닙니다: {path.name}]")

    pdf_bytes = path.read_bytes()
    logger.info(f"Loaded PDF: {path.name} ({len(pdf_bytes)} bytes)")
    return pdf_bytes, "application/pdf"
