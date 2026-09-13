"""Connectivity guard for diagnosing API Keys and offline isolation."""

from typing import Tuple, Optional
from jarvis.utils.config import JarvisConfig, load_config
from jarvis.utils.logger import get_logger

logger = get_logger("guardrails.connectivity")


class ConnectivityGuard:
    """Validates connectivity states, API keys, and offline mode assurances."""

    def __init__(self, config: Optional[JarvisConfig] = None):
        self.config = config or load_config()

    def diagnose_provider(self, provider_name: str) -> Tuple[bool, str]:
        """Diagnose readiness for specified LLM provider with user-friendly advice."""
        norm_name = provider_name.lower().strip()

        if norm_name in ("gemini", "google", "cloud"):
            key = self.config.gemini_api_key
            if not key or key.strip() in ("", "your_gemini_api_key_here"):
                return False, (
                    "[Gemini 미설정] GEMINI_API_KEY가 등록되지 않았습니다.\n"
                    "👉 조치 방법:\n"
                    "  1. Google AI Studio(https://aistudio.google.com/app/apikey)에서 무료 API Key 발급\n"
                    "  2. 'config/.env' 파일에 GEMINI_API_KEY=AIzaSy... 입력 후 저장"
                )
            return True, "Google Gemini 클라우드 API 연결 정상 준비 완료."

        elif norm_name in ("ollama", "local"):
            host = self.config.llm.ollama.host
            model = self.config.llm.ollama.model
            return True, f"Ollama 로컬 엔진({host} / 모델: {model}) 오프라인 모드 준비 완료."

        return False, f"알 수 없는 프로바이더: '{provider_name}'"
