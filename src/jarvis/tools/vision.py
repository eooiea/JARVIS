"""Vision analysis tools supporting single document and batch multi-file extraction."""

from pathlib import Path
from typing import Union, List, Dict, Any, Optional
from jarvis.vision.capture import ScreenCapture
from jarvis.vision.file_input import load_image_file, load_pdf_file
from jarvis.vision.analyzer import VisionAnalyzer
from jarvis.providers.base import BaseLLMProvider
from jarvis.utils.logger import get_logger

logger = get_logger("tools.vision")


def capture_screen(region: Optional[tuple] = None) -> bytes:
    """Capture full screen or specific bounding box region."""
    capturer = ScreenCapture()
    if region and len(region) == 4:
        return capturer.capture_region(x=region[0], y=region[1], width=region[2], height=region[3])
    return capturer.capture_full_screen()


def analyze_document(
    file_or_bytes: Union[str, Path, bytes],
    provider: Optional[BaseLLMProvider] = None,
    prompt: Optional[str] = None,
) -> Dict[str, Any]:
    """Analyze a single visual document (image/pdf/bytes) using Gemini vision."""
    analyzer = VisionAnalyzer(provider=provider)

    if isinstance(file_or_bytes, (str, Path)):
        path = Path(file_or_bytes).resolve()
        if path.suffix.lower() == ".pdf":
            img_bytes, mime_type = load_pdf_file(path)
        else:
            img_bytes, mime_type = load_image_file(path)
    else:
        img_bytes = file_or_bytes
        mime_type = "image/png"

    return analyzer.analyze_structured_data(
        image_bytes=img_bytes,
        mime_type=mime_type,
        prompt=prompt,
    )


def batch_analyze_documents(
    file_paths: List[Union[str, Path]],
    provider: Optional[BaseLLMProvider] = None,
    prompt: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """Batch analyze multiple document files and return aggregated list of parsed records."""
    logger.info(f"Starting batch analysis for {len(file_paths)} document files...")
    aggregated_results: List[Dict[str, Any]] = []

    for idx, path_item in enumerate(file_paths, start=1):
        path = Path(path_item).resolve()
        logger.info(f"[{idx}/{len(file_paths)}] Processing: {path.name}")
        try:
            record = analyze_document(path, provider=provider, prompt=prompt)
            # Tag source filename
            if isinstance(record, dict):
                record["_source_file"] = path.name
                aggregated_results.append(record)
            elif isinstance(record, list):
                for item in record:
                    if isinstance(item, dict):
                        item["_source_file"] = path.name
                    aggregated_results.append(item)
        except Exception as e:
            logger.error(f"Failed to analyze '{path.name}': {e}")

    logger.info(f"Batch analysis completed. Extracted {len(aggregated_results)} records.")
    return aggregated_results
