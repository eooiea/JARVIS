"""Unit tests for JARVIS Autonomous ReAct Agent (TDD Red-Green)."""

import pytest
from unittest.mock import MagicMock
from jarvis.brain.agent import JarvisAgent, AgentResponse, ToolCall
from jarvis.tools.registry import ToolRegistry


def test_agent_react_loop_executes_tools_until_final_answer():
    """Agent should loop: receive tool_call from LLM -> execute tool -> feed observation back -> stop on final text."""
    registry = ToolRegistry()

    def mock_scan(path: str):
        """Scan directory tool."""
        return [{"name": "file1.txt", "size": "100 B"}]

    registry.register(mock_scan)

    # Mock Provider
    mock_provider = MagicMock()
    # Turn 1: LLM decides to call mock_scan
    # Turn 2: LLM receives observation and produces final answer
    mock_provider.chat_with_tools.side_effect = [
        AgentResponse(
            thought="폴더 스캔 도구를 먼저 호출해야겠다.",
            tool_calls=[ToolCall(name="mock_scan", args={"path": "C:/my_project"})],
            text=None,
        ),
        AgentResponse(
            thought="파일 1개가 확인되었으니 보고서를 작성한다.",
            tool_calls=[],
            text="C:/my_project 폴더에 file1.txt가 확인되었습니다.",
        ),
    ]

    agent = JarvisAgent(provider=mock_provider, tool_registry=registry, max_turns=5)
    final_output = agent.run("C:/my_project 폴더 확인해줘")

    assert "file1.txt가 확인되었습니다" in final_output
    assert mock_provider.chat_with_tools.call_count == 2


def test_agent_max_turns_safeguard():
    """Agent should terminate gracefully if LLM enters an infinite tool call loop."""
    registry = ToolRegistry()

    def endless_tool():
        """Endless tool."""
        return "looping"

    registry.register(endless_tool)

    mock_provider = MagicMock()
    # LLM always calls endless_tool
    mock_provider.chat_with_tools.return_value = AgentResponse(
        thought="계속 호출한다.",
        tool_calls=[ToolCall(name="endless_tool", args={})],
        text=None,
    )

    agent = JarvisAgent(provider=mock_provider, tool_registry=registry, max_turns=3)
    final_output = agent.run("무한 반복 명령")

    assert "최대 실행 횟수" in final_output or "중단" in final_output
    assert mock_provider.chat_with_tools.call_count == 3
