"""Vision Anchor Finder for detecting UI element and form input coordinates."""

import json
import re
from typing import Optional, Tuple
from jarvis.providers.base import BaseLLMProvider
from jarvis.providers.factory import get_llm_provider
from jarvis.utils.logger import get_logger

logger = get_logger("vision.anchor")

ANCHOR_PROMPT_TEMPLATE = """당신은 정밀한 Windows GUI UI 분석 비전 AI입니다.
주어진 화면 캡처에서 사용자가 지정한 타겟 요소(버튼, 입력 필드 등)의 클릭 가능한 중심 좌표 (x, y)를 찾아주세요.

[찾을 대상]: "{target_label}"

[응답 형식]:
반드시 오직 아래의 유효한 JSON 형식으로만 응답하세요:
{{
  "found": true,
  "x": 350,
  "y": 420
}}
만약 화면에서 해당 요소를 전혀 찾을 수 없다면:
{{
  "found": false
}}
"""


class VisionAnchorFinder:
    """Finds screen pixel coordinates (x, y) for UI elements based on vision."""

    def __init__(self, provider: Optional[BaseLLMProvider] = None):
        self.provider = provider or get_llm_provider("gemini")

    def _clean_json_text(self, text: str) -> str:
        cleaned = text.strip()
        json_match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", cleaned, re.IGNORECASE)
        if json_match:
            cleaned = json_match.group(1).strip()
        return cleaned

    def find_anchor(
        self,
        image_bytes: bytes,
        target_label: str,
        mime_type: str = "image/png",
    ) -> Optional[Tuple[int, int]]:
        """Detect (x, y) coordinate anchor for specified target UI element."""
        prompt = ANCHOR_PROMPT_TEMPLATE.format(target_label=target_label)
        logger.info(f"Detecting UI Anchor for: '{target_label}'")

        raw_response = self.provider.generate_with_image(
            prompt=prompt,
            image_bytes=image_bytes,
            mime_type=mime_type,
        )

        cleaned_json = self._clean_json_text(raw_response)
        try:
            parsed = json.loads(cleaned_json)
            if parsed.get("found") is True and "x" in parsed and "y" in parsed:
                x = int(parsed["x"])
                y = int(parsed["y"])
                logger.info(f"Detected UI Anchor at ({x}, {y}) for '{target_label}'")
                return x, y
            else:
                logger.warning(f"UI Anchor not found for '{target_label}'")
                return None
        except Exception as e:
            logger.error(f"Failed to parse Anchor coordinates from response: {e}")
            return None
