"""Ollama Local LLM Provider (Offline Korean Text & Fast Data Structuring)."""

from typing import Optional
import ollama
from jarvis.providers.base import BaseLLMProvider, LLMConnectionError
from jarvis.utils.config import JarvisConfig, load_config
from jarvis.utils.logger import get_logger

logger = get_logger("providers.ollama")


class OllamaProvider(BaseLLMProvider):
    """Ollama Local LLM Provider for offline Korean processing and data structuring."""

    def __init__(self, config: Optional[JarvisConfig] = None):
        self.config = config or load_config()
        self.host = self.config.llm.ollama.host
        self.model = self.config.llm.ollama.model
        self.temperature = self.config.llm.ollama.temperature

        self.vision_model = getattr(self.config.llm.ollama, "vision_model", "llava-llama3:latest")

        try:
            self.client = ollama.Client(host=self.host)
        except Exception as e:
            raise LLMConnectionError(
                f"[Ollama 초기화 실패] {type(e).__name__}: {str(e)}\n"
                f"호스트 URL({self.host})을 확인해주세요."
            )

    def generate(self, prompt: str, system_instruction: Optional[str] = None, **kwargs) -> str:
        """Generate text completion using local Ollama model."""
        model_name = kwargs.get("model", self.model)
        temperature = kwargs.get("temperature", self.temperature)

        messages = []
        if system_instruction:
            messages.append({"role": "system", "content": system_instruction})
        messages.append({"role": "user", "content": prompt})

        options = {}
        if temperature is not None:
            options["temperature"] = temperature

        try:
            response = self.client.chat(
                model=model_name,
                messages=messages,
                options=options if options else None,
            )
            return response.get("message", {}).get("content", "")
        except Exception as e:
            logger.error(f"Ollama local chat error: {e}")
            raise LLMConnectionError(
                f"[Ollama 로컬 서버에 연결할 수 없습니다] {type(e).__name__}: {str(e)}\n"
                "👉 조치 방법:\n"
                "  1. 터미널에서 'ollama serve' 또는 Ollama 앱이 실행 중인지 확인\n"
                f"  2. 'ollama pull {model_name}' 명령어로 모델이 설치되어 있는지 확인"
            )

    def generate_with_image(
        self,
        prompt: str,
        image_bytes: bytes,
        mime_type: str = "image/png",
        system_instruction: Optional[str] = None,
        **kwargs,
    ) -> str:
        """Process image using local multimodal Ollama model (llava-llama3)."""
        import base64
        model_name = kwargs.get("model", self.vision_model)
        b64_image = base64.b64encode(image_bytes).decode("utf-8")

        messages = []
        if system_instruction:
            messages.append({"role": "system", "content": system_instruction})
        messages.append({
            "role": "user",
            "content": prompt,
            "images": [b64_image],
        })

        try:
            response = self.client.chat(
                model=model_name,
                messages=messages,
            )
            return response.get("message", {}).get("content", "")
        except Exception as e:
            logger.error(f"Ollama local vision error: {e}")
            raise LLMConnectionError(
                f"[Ollama 비전 모델 실행 실패] {type(e).__name__}: {str(e)}\n"
                f"모델 '{model_name}'이 정상 설치되어 있는지 확인해주세요 ('ollama pull {model_name}')."
            )

    def chat_with_tools(
        self,
        messages: list,
        tools: list,
        **kwargs,
    ) -> "AgentResponse":
        """Execute tool-calling reasoning turn using local Ollama model."""
        import json
        import re
        from jarvis.providers.base import ToolCall, AgentResponse

        tools_desc = json.dumps(tools, ensure_ascii=False, indent=2)
        system_instruction = (
            "당신은 Windows 환경에서 사용자의 모든 작업을 완결짓는 자율 AI 에이전트 JARVIS의 두뇌입니다.\n"
            "사용자의 목표를 달성하기 위해 아래 제공된 도구(Tools)들을 적절히 호출하십시오.\n\n"
            f"[사용 가능한 도구 목록 (JSON Schema)]:\n{tools_desc}\n\n"
            "[응답 규칙]:\n"
            "반드시 아래 JSON 포맷으로만 응답해야 합니다:\n"
            "{\n"
            '  "thought": "현재 상황에 대한 분석 및 다음 행동 이유",\n'
            '  "tool_calls": [\n'
            '    {"name": "호출할_도구이름", "args": {"인자명": "값"}}\n'
            "  ],\n"
            '  "final_answer": "모든 작업이 완결되었을 때 사용자에게 전할 최종 보고 텍스트 (도구를 호출할 때는 null)"\n'
            "}\n"
            "주의: 더 이상 호출할 도구가 없고 작업이 완료되었을 때만 'tool_calls'를 빈 배열 []로 하고 'final_answer'에 최종 보고를 작성하십시오."
        )

        # Collect existing system prompts from agent (Blackboard, Taboo list, Protocols)
        agent_system_prompts = [m.get("content", "") for m in messages if m.get("role") == "system"]
        if agent_system_prompts:
            effective_system = "\n\n".join(agent_system_prompts) + "\n\n" + (
                f"[사용 가능한 도구 목록 (JSON Schema)]:\n{tools_desc}\n\n"
                "[응답 규칙]:\n"
                "반드시 아래 JSON 포맷으로만 응답해야 합니다:\n"
                "{\n"
                '  "thought": "현재 상황에 대한 분석 및 다음 행동 이유",\n'
                '  "blackboard": {\n'
                '    "phase": "현재 작업 단계 (예: SEARCH, PROCESS, VERIFY, COMPLETE)",\n'
                '    "update_milestones": [{"id": 1, "status": "DONE"}, {"id": 2, "status": "IN_PROGRESS"}],\n'
                '    "add_findings": {"발견항목": "내용"}\n'
                '  },\n'
                '  "tool_calls": [\n'
                '    {"name": "호출할_도구이름", "args": {"인자명": "값"}}\n'
                "  ],\n"
                '  "final_answer": "모든 작업이 완결되었을 때 사용자에게 전할 최종 보고 텍스트 (도구를 호출할 때는 null)"\n'
                "}\n"
                "주의: 도구를 호출한 결과가 이미 대화 히스토리에 주어져 있다면, 같은 도구를 반복 호출하지 말고 관측 결과를 종합하여 'final_answer'로 보고를 작성하십시오."
            )
        else:
            effective_system = system_instruction

        formatted_messages = [{"role": "system", "content": effective_system}]
        for msg in messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            name = msg.get("name", "")
            if role == "tool":
                formatted_messages.append({"role": "user", "content": f"[도구 실행 결과 ({name})]:\n{content}"})
            elif role == "system":
                continue
            elif role == "assistant":
                tc_list = msg.get("tool_calls", [])
                if tc_list:
                    tc_desc = ", ".join(f"{tc.get('name')}({tc.get('args', {})})" for tc in tc_list)
                    formatted_messages.append({
                        "role": "assistant",
                        "content": f"{content}\n[호출한 도구: {tc_desc}]" if content else f"[호출한 도구: {tc_desc}]",
                    })
                else:
                    formatted_messages.append({"role": "assistant", "content": content})
            else:
                formatted_messages.append({"role": role, "content": content})

        try:
            response = self.client.chat(
                model=kwargs.get("model", self.model),
                messages=formatted_messages,
                format="json",
            )
            raw_text = response.get("message", {}).get("content", "")

            # Clean json fences if any
            cleaned = raw_text.strip()
            if cleaned.startswith("```"):
                cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
                cleaned = re.sub(r"\s*```$", "", cleaned)

            parsed = json.loads(cleaned)
            thought = parsed.get("thought")
            final_answer = parsed.get("final_answer")
            blackboard = parsed.get("blackboard") or {}
            tool_calls = []

            for tc in parsed.get("tool_calls", []):
                tool_calls.append(ToolCall(name=tc.get("name"), args=tc.get("args", {})))

            return AgentResponse(
                thought=thought,
                tool_calls=tool_calls,
                text=final_answer,
                blackboard_delta=blackboard,
            )
        except Exception as e:
            logger.warning(f"Failed to parse tool call JSON from Ollama ({e}), falling back to direct text.")
            return AgentResponse(
                thought="직접 응답",
                tool_calls=[],
                text=raw_text if 'raw_text' in locals() and raw_text else str(e),
            )

