"""Google Gemini LLM Provider (Cloud Multimodal & Fast Vision)."""

from typing import Optional
from google import genai
from google.genai import types
from jarvis.providers.base import BaseLLMProvider, LLMConnectionError
from jarvis.utils.config import JarvisConfig, load_config
from jarvis.utils.logger import get_logger

logger = get_logger("providers.gemini")


class GeminiProvider(BaseLLMProvider):
    """Google Gemini API Provider for vision, complex multimodal, and fast reasoning."""

    def __init__(self, config: Optional[JarvisConfig] = None):
        self.config = config or load_config()
        self.api_key = self.config.gemini_api_key
        self.model = self.config.llm.gemini.model
        self.temperature = self.config.llm.gemini.temperature

        if not self.api_key or self.api_key.strip() in ("", "your_gemini_api_key_here"):
            raise LLMConnectionError(
                "[Gemini 연결 오류] GEMINI_API_KEY가 설정되지 않았습니다.\n"
                "👉 조치 방법:\n"
                "  1. Google AI Studio(https://aistudio.google.com/app/apikey)에서 무료 API Key 발급\n"
                "  2. 'config/.env' 파일에 GEMINI_API_KEY=AIzaSy... 입력 후 저장"
            )

        try:
            self.client = genai.Client(api_key=self.api_key)
        except Exception as e:
            raise LLMConnectionError(
                f"[Gemini 클라이언트 초기화 실패] {type(e).__name__}: {str(e)}\n"
                "인터넷 연결 상태 및 API 키 유효성을 확인해주세요."
            )

    def generate(self, prompt: str, system_instruction: Optional[str] = None, **kwargs) -> str:
        """Generate text using Gemini."""
        model_name = kwargs.get("model", self.model)
        temperature = kwargs.get("temperature", self.temperature)

        config_params = {}
        if system_instruction:
            config_params["system_instruction"] = system_instruction
        if temperature is not None:
            config_params["temperature"] = temperature

        gen_config = types.GenerateContentConfig(**config_params) if config_params else None

        import time
        max_retries = 3
        delay = 1.5

        for attempt in range(1, max_retries + 1):
            try:
                response = self.client.models.generate_content(
                    model=model_name,
                    contents=prompt,
                    config=gen_config,
                )
                return response.text or ""
            except Exception as e:
                err_str = str(e)
                if ("503" in err_str or "UNAVAILABLE" in err_str or "429" in err_str) and attempt < max_retries:
                    logger.warning(f"Gemini API 503/429 temporary spike (attempt {attempt}/{max_retries}). Retrying in {delay:.1f}s...")
                    time.sleep(delay)
                    delay *= 1.5
                    continue
                logger.error(f"Gemini API generation error: {e}")
                raise LLMConnectionError(
                    f"[Gemini API 호출 중 오류가 발생했습니다] {type(e).__name__}: {str(e)}\n"
                    "네트워크 연결을 확인하거나 잠시 후 다시 시도해주세요."
                )

    def generate_with_image(
        self,
        prompt: str,
        image_bytes: bytes,
        mime_type: str = "image/png",
        system_instruction: Optional[str] = None,
        **kwargs,
    ) -> str:
        """Analyze image with Gemini vision multimodal."""
        model_name = kwargs.get("model", self.model)
        temperature = kwargs.get("temperature", self.temperature)

        config_params = {}
        if system_instruction:
            config_params["system_instruction"] = system_instruction
        if temperature is not None:
            config_params["temperature"] = temperature

        gen_config = types.GenerateContentConfig(**config_params) if config_params else None

        try:
            image_part = types.Part.from_bytes(data=image_bytes, mime_type=mime_type)
            response = self.client.models.generate_content(
                model=model_name,
                contents=[prompt, image_part],
                config=gen_config,
            )
            return response.text or ""
        except Exception as e:
            logger.error(f"Gemini multimodal error: {e}")
            raise LLMConnectionError(
                f"[Gemini 멀티모달 API 호출 실패] {type(e).__name__}: {str(e)}\n"
                "이미지 규격(용량, 포맷) 및 Google API 할당량을 확인해주세요."
            )

    def chat_with_tools(
        self,
        messages: list,
        tools: list,
        **kwargs,
    ) -> "AgentResponse":
        """Execute tool-calling reasoning turn using structured JSON schema."""
        import json
        from jarvis.providers.base import ToolCall, AgentResponse

        tools_desc = json.dumps(tools, ensure_ascii=False, indent=2)
        system_instruction = (
            "당신은 Windows 환경에서 사용자의 모든 작업을 완결짓는 자율 AI 에이전트 JARVIS의 두뇌입니다.\n"
            "사용자의 목표를 달성하기 위해 아래 제공된 도구(Tools)들을 적절히 호출하십시오.\n\n"
            f"[사용 가능한 도구 목록 (JSON Schema)]:\n{tools_desc}\n\n"
            "[응답 규칙]:\n"
            "반드시 아래 JSON 포맷으로만 응답해야 합니다 (마크다운 백틱 포함/미포함 가능):\n"
            "{\n"
            '  "thought": "현재 상황에 대한 분석 및 다음 행동 이유",\n'
            '  "tool_calls": [\n'
            '    {"name": "호출할_도구이름", "args": {"인자명": "값"}}\n'
            "  ],\n"
            '  "final_answer": "모든 작업이 완결되었을 때 사용자에게 전할 최종 보고 텍스트 (도구를 호출할 때는 null)"\n'
            "}\n"
            "주의: 더 이상 호출할 도구가 없고 작업이 완료되었을 때만 'tool_calls'를 빈 배열 []로 하고 'final_answer'에 최종 보고를 작성하십시오."
        )

        # Build prompt transcript
        history_lines = []
        for msg in messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            name = msg.get("name", "")
            if role == "tool":
                history_lines.append(f"[Tool Result ({name})]: {content}")
            elif role == "user":
                history_lines.append(f"[User]: {content}")
            else:
                history_lines.append(f"[{role}]: {content}")

        full_prompt = "\n".join(history_lines) + "\n\n다음 행동을 JSON으로 결정하십시오:"

        try:
            raw_text = self.generate(
                prompt=full_prompt,
                system_instruction=system_instruction,
            )

            # Strip markdown fences if present
            cleaned = raw_text.strip()
            if cleaned.startswith("```"):
                lines = cleaned.splitlines()
                if lines[0].startswith("```"):
                    lines = lines[1:]
                if lines and lines[-1].startswith("```"):
                    lines = lines[:-1]
                cleaned = "\n".join(lines).strip()

            parsed = json.loads(cleaned)
            thought = parsed.get("thought")
            final_answer = parsed.get("final_answer")
            tool_calls = []

            for tc in parsed.get("tool_calls", []):
                tool_calls.append(ToolCall(name=tc.get("name"), args=tc.get("args", {})))

            return AgentResponse(
                thought=thought,
                tool_calls=tool_calls,
                text=final_answer,
            )
        except Exception as e:
            logger.warning(f"Failed to parse tool call JSON from Gemini ({e}), falling back to direct text.")
            return AgentResponse(thought="직접 응답", tool_calls=[], text=raw_text if 'raw_text' in locals() else str(e))
