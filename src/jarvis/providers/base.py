from abc import ABC, abstractmethod
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field


class ToolCall(BaseModel):
    """Represents a tool invocation requested by LLM."""
    name: str
    args: Dict[str, Any] = Field(default_factory=dict)


class AgentResponse(BaseModel):
    """LLM response containing thoughts, tool calls, and/or final answer."""
    thought: Optional[str] = None
    tool_calls: List[ToolCall] = Field(default_factory=list)
    text: Optional[str] = None
    blackboard_delta: Dict[str, Any] = Field(default_factory=dict)
    raw_prompt: Optional[str] = None
    raw_response: Optional[str] = None



class LLMConnectionError(Exception):
    """Raised when an LLM provider fails to connect, authenticate, or execute."""
    pass


class BaseLLMProvider(ABC):
    """Abstract Base Class for all LLM providers (Cloud & Local)."""

    @abstractmethod
    def generate(self, prompt: str, system_instruction: Optional[str] = None, **kwargs) -> str:
        """Generate text completion from text prompt."""
        pass

    @abstractmethod
    def generate_with_image(
        self,
        prompt: str,
        image_bytes: bytes,
        mime_type: str = "image/png",
        system_instruction: Optional[str] = None,
        **kwargs,
    ) -> str:
        """Generate multimodal completion from text prompt and image bytes."""
        pass

    def chat_with_tools(
        self,
        messages: List[Dict[str, Any]],
        tools: List[Dict[str, Any]],
        **kwargs,
    ) -> AgentResponse:
        """Run tool-calling chat turn with list of messages and tool schemas."""
        raise NotImplementedError("This provider does not implement chat_with_tools.")
