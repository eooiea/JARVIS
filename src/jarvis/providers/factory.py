"""Factory for creating and routing LLM Provider instances."""

from typing import Optional
from jarvis.providers.base import BaseLLMProvider
from jarvis.providers.gemini import GeminiProvider
from jarvis.providers.ollama import OllamaProvider
from jarvis.utils.config import JarvisConfig, load_config


class LLMProviderFactory:
    """Factory class to create concrete LLM providers based on name or config."""

    @staticmethod
    def create(name: str, config: Optional[JarvisConfig] = None) -> BaseLLMProvider:
        """Create and return an LLM provider instance."""
        cfg = config or load_config()
        normalized_name = name.lower().strip()

        if normalized_name in ("gemini", "google", "cloud"):
            return GeminiProvider(config=cfg)
        elif normalized_name in ("ollama", "local", "qwen"):
            return OllamaProvider(config=cfg)
        else:
            raise ValueError(
                f"[지원하지 않는 LLM 프로바이더입니다: '{name}']\n"
                "사용 가능한 프로바이더: 'gemini', 'ollama'"
            )


def get_llm_provider(name: Optional[str] = None, config: Optional[JarvisConfig] = None) -> BaseLLMProvider:
    """Convenience helper to get default or named LLM provider."""
    cfg = config or load_config()
    provider_name = name or cfg.llm.default_provider
    return LLMProviderFactory.create(provider_name, config=cfg)
