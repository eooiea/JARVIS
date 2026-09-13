"""Unit tests for JARVIS Hybrid LLM Providers (TDD Red-Green)."""

import pytest
from unittest.mock import MagicMock, patch
from jarvis.utils.config import JarvisConfig, GeminiConfig, OllamaConfig
from jarvis.providers.base import BaseLLMProvider, LLMConnectionError
from jarvis.providers.gemini import GeminiProvider
from jarvis.providers.ollama import OllamaProvider
from jarvis.providers.factory import LLMProviderFactory, get_llm_provider


# ==========================================
# 1. Base / Abstract Provider Tests
# ==========================================
def test_base_provider_cannot_be_instantiated():
    """BaseLLMProvider is an abstract class and cannot be instantiated directly."""
    with pytest.raises(TypeError):
        BaseLLMProvider()  # type: ignore


# ==========================================
# 2. GeminiProvider Tests
# ==========================================
def test_gemini_provider_missing_api_key():
    """GeminiProvider should raise LLMConnectionError when API key is missing."""
    config = JarvisConfig(gemini_api_key=None)
    with pytest.raises(LLMConnectionError) as exc_info:
        GeminiProvider(config=config)
    assert "GEMINI_API_KEY" in str(exc_info.value)
    assert "Google AI Studio" in str(exc_info.value)


@patch("jarvis.providers.gemini.genai.Client")
def test_gemini_provider_text_generation(mock_client_cls):
    """GeminiProvider text generation should call google-genai client and return text."""
    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.text = "안녕하세요! JARVIS입니다."
    mock_client.models.generate_content.return_value = mock_response
    mock_client_cls.return_value = mock_client

    config = JarvisConfig(gemini_api_key="AIzaSyTestKey")
    provider = GeminiProvider(config=config)
    result = provider.generate("안녕")

    assert result == "안녕하세요! JARVIS입니다."
    mock_client.models.generate_content.assert_called_once()


@patch("jarvis.providers.gemini.genai.Client")
def test_gemini_provider_image_generation(mock_client_cls):
    """GeminiProvider multimodal image analysis should process image bytes."""
    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.text = '{"total": 15000, "item": "식대"}'
    mock_client.models.generate_content.return_value = mock_response
    mock_client_cls.return_value = mock_client

    config = JarvisConfig(gemini_api_key="AIzaSyTestKey")
    provider = GeminiProvider(config=config)
    dummy_image_bytes = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR"
    result = provider.generate_with_image("영수증 분석해줘", dummy_image_bytes)

    assert result == '{"total": 15000, "item": "식대"}'
    mock_client.models.generate_content.assert_called_once()


@patch("jarvis.providers.gemini.genai.Client")
def test_gemini_provider_api_failure_handling(mock_client_cls):
    """GeminiProvider should wrap genai exceptions into user-friendly LLMConnectionError."""
    mock_client = MagicMock()
    mock_client.models.generate_content.side_effect = Exception("API Quota Exceeded")
    mock_client_cls.return_value = mock_client

    config = JarvisConfig(gemini_api_key="AIzaSyTestKey")
    provider = GeminiProvider(config=config)

    with pytest.raises(LLMConnectionError) as exc_info:
        provider.generate("테스트")
    assert "Gemini API 호출 중 오류가 발생했습니다" in str(exc_info.value)


# ==========================================
# 3. OllamaProvider Tests
# ==========================================
@patch("jarvis.providers.ollama.ollama.Client")
def test_ollama_provider_text_generation(mock_ollama_client_cls):
    """OllamaProvider should call local Ollama chat API and return response text."""
    mock_client = MagicMock()
    mock_client.chat.return_value = {
        "message": {"content": "로컬 Qwen 모델 응답입니다."}
    }
    mock_ollama_client_cls.return_value = mock_client

    config = JarvisConfig()
    provider = OllamaProvider(config=config)
    result = provider.generate("로컬 텍스트 분석해줘")

    assert result == "로컬 Qwen 모델 응답입니다."
    mock_client.chat.assert_called_once()


@patch("jarvis.providers.ollama.ollama.Client")
def test_ollama_provider_connection_failure(mock_ollama_client_cls):
    """OllamaProvider should raise LLMConnectionError when Ollama server is unreachable."""
    mock_client = MagicMock()
    mock_client.chat.side_effect = Exception("Connection refused to 11434")
    mock_ollama_client_cls.return_value = mock_client

    config = JarvisConfig()
    provider = OllamaProvider(config=config)

    with pytest.raises(LLMConnectionError) as exc_info:
        provider.generate("테스트")
    assert "Ollama 로컬 서버에 연결할 수 없습니다" in str(exc_info.value)
    assert "ollama serve" in str(exc_info.value)


@patch("jarvis.providers.ollama.ollama.Client")
def test_ollama_provider_chat_with_tools(mock_ollama_client_cls):
    """OllamaProvider should format tools and return parsed AgentResponse."""
    mock_client = MagicMock()
    mock_client.chat.return_value = {
        "message": {
            "content": '{"thought": "디렉터리를 스캔합니다.", "tool_calls": [{"name": "scan_directory", "args": {"path": "C:/test"}}], "final_answer": null}'
        }
    }
    mock_ollama_client_cls.return_value = mock_client

    config = JarvisConfig()
    provider = OllamaProvider(config=config)
    messages = [{"role": "user", "content": "C:/test 스캔해줘"}]
    tools = [{"name": "scan_directory", "description": "스캔"}]

    response = provider.chat_with_tools(messages, tools=tools)

    assert response.thought == "디렉터리를 스캔합니다."
    assert len(response.tool_calls) == 1
    assert response.tool_calls[0].name == "scan_directory"
    assert response.tool_calls[0].args == {"path": "C:/test"}
    assert response.text is None
    mock_client.chat.assert_called_once()


@patch("jarvis.providers.ollama.ollama.Client")
def test_ollama_provider_image_generation(mock_ollama_client_cls):
    """OllamaProvider should support local multimodal vision via vision_model (llava)."""
    mock_client = MagicMock()
    mock_client.chat.return_value = {
        "message": {"content": '{"total": 5000, "item": "커피"}'}
    }
    mock_ollama_client_cls.return_value = mock_client

    config = JarvisConfig()
    provider = OllamaProvider(config=config)
    dummy_image_bytes = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR"
    result = provider.generate_with_image("영수증 분석해줘", dummy_image_bytes)

    assert result == '{"total": 5000, "item": "커피"}'
    mock_client.chat.assert_called_once()



# ==========================================
# 4. LLMProviderFactory Tests
# ==========================================
def test_factory_returns_gemini_provider():
    """Factory should return GeminiProvider instance when requested."""
    config = JarvisConfig(gemini_api_key="AIzaSyTestKey")
    with patch("jarvis.providers.gemini.genai.Client"):
        provider = LLMProviderFactory.create("gemini", config=config)
        assert isinstance(provider, GeminiProvider)


def test_factory_returns_ollama_provider():
    """Factory should return OllamaProvider instance when requested."""
    config = JarvisConfig()
    provider = LLMProviderFactory.create("ollama", config=config)
    assert isinstance(provider, OllamaProvider)


def test_factory_unknown_provider_raises_error():
    """Factory should raise ValueError for unsupported provider names."""
    with pytest.raises(ValueError) as exc_info:
        LLMProviderFactory.create("unknown_provider")
    assert "지원하지 않는 LLM 프로바이더" in str(exc_info.value)
