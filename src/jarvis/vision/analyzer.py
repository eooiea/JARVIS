"""Vision Analyzer for extracting structured JSON data from visual documents."""

import json
import re
from typing import Optional, Dict, Any
from jarvis.providers.base import BaseLLMProvider
from jarvis.providers.factory import get_llm_provider
from jarvis.utils.logger import get_logger

logger = get_logger("vision.analyzer")

DEFAULT_EXTRACTION_PROMPT = """당신은 최고 수준의 문서/영수증/표 정형화 전문 AI입니다.
주어진 이미지 또는 화면 캡처를 정밀하게 분석하여 순수 JSON 포맷으로 추출해주세요.

[반환 형식 요구사항]
1. 불필요한 설명 없이 오직 유효한 JSON 포맷만 반환하세요.
2. 금액(숫자), 날짜, 항목명, 수량, 공급가액, 부가세, 합계 등을 누락 없이 정형화하세요.
3. 표 형태인 경우 "headers"와 "rows" 또는 객체 배열 형태("items")로 구조화하세요.
"""


class VisionAnalyzer:
    """Extracts structured JSON dictionaries from images or PDF documents."""

    def __init__(self, provider: Optional[BaseLLMProvider] = None):
        # Default to configured provider (Gemini or Ollama)
        self.provider = provider or get_llm_provider()

    def _clean_json_text(self, text: str) -> str:
        """Strip markdown code block fences and extract clean JSON string."""
        cleaned = text.strip()
        # Match ```json ... ``` or ``` ... ```
        json_match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", cleaned, re.IGNORECASE)
        if json_match:
            cleaned = json_match.group(1).strip()
        return cleaned

    def analyze_structured_data(
        self,
        image_bytes: bytes,
        mime_type: str = "image/png",
        prompt: Optional[str] = None,
        system_instruction: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Send image to VLM and parse structured JSON result."""
        final_prompt = prompt or DEFAULT_EXTRACTION_PROMPT
        logger.info(f"Analyzing visual document ({len(image_bytes)} bytes, {mime_type})")

        raw_response = self.provider.generate_with_image(
            prompt=final_prompt,
            image_bytes=image_bytes,
            mime_type=mime_type,
            system_instruction=system_instruction,
        )

        cleaned_json = self._clean_json_text(raw_response)
        try:
            parsed_data = json.loads(cleaned_json)
            logger.info("Successfully parsed structured JSON data.")
            return parsed_data
        except json.JSONDecodeError as e:
            logger.error(f"JSON parsing failed: {e}. Raw response: {raw_response[:200]}")
            raise ValueError(
                f"[JSON 파싱 실패] AI 응답이 유효한 JSON 형식이 아닙니다: {e}\n"
                f"원문 응답: {raw_response[:300]}"
            )
