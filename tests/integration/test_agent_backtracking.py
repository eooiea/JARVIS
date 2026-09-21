"""Integration tests for JARVIS Agent Blackboard & Backtracking Engine."""

import shutil
import tempfile
from pathlib import Path
from unittest.mock import MagicMock
import pytest

from jarvis.brain.agent import JarvisAgent
from jarvis.providers.base import AgentResponse, ToolCall
from jarvis.tools.registry import ToolRegistry


class TestAgentBacktrackingIntegration:
    """End-to-end integration tests verifying rollback, context pruning, and recovery."""

    @pytest.fixture
    def test_env(self):
        temp_dir = tempfile.mkdtemp(prefix="jarvis_backtrack_e2e_")
        workspace = Path(temp_dir) / "workspace"
        workspace.mkdir()
        staging_dir = Path(temp_dir) / "staging"
        staging_dir.mkdir()

        yield str(workspace), str(staging_dir)

        shutil.rmtree(temp_dir, ignore_errors=True)

    def test_agent_rolls_back_on_tool_failure_and_succeeds_with_plan_b(self, test_env):
        """Simulate Tool failure on Turn 1 -> Rollback with Taboo -> Plan B on Turn 2 -> Complete on Turn 3."""
        workspace, staging_dir = test_env
        registry = ToolRegistry()

        # Tools
        def parse_broken_csv(filename: str):
            """Broken parsing tool."""
            return "Error: Encoding failure - CP949 bytes corrupted"

        def parse_valid_json(filename: str):
            """Alternative working tool."""
            return "Success: Extracted 10 items from JSON"

        registry.register(parse_broken_csv)
        registry.register(parse_valid_json)

        # Mock LLM Provider
        mock_provider = MagicMock()
        mock_provider.chat_with_tools.side_effect = [
            # Turn 1: Attempt broken CSV tool
            AgentResponse(
                thought="CSV 파일을 열어보겠습니다.",
                tool_calls=[ToolCall(name="parse_broken_csv", args={"filename": "data.csv"})],
                text=None,
            ),
            # Turn 2: Sees taboo lesson in prompt, attempts Plan B with JSON
            AgentResponse(
                thought="직전 CSV 파싱이 실패했으므로 JSON 파서를 시도합니다.",
                tool_calls=[ToolCall(name="parse_valid_json", args={"filename": "data.json"})],
                text=None,
            ),
            # Turn 3: Finished
            AgentResponse(
                thought="모든 데이터가 정상 취합되었습니다.",
                tool_calls=[],
                text="데이터 취합 완료: 10건",
            ),
        ]

        agent = JarvisAgent(
            provider=mock_provider,
            tool_registry=registry,
            max_turns=5,
            workspace_root=workspace,
        )

        result = agent.run("데이터 파일을 취합해줘")

        assert "데이터 취합 완료: 10건" in result
        assert mock_provider.chat_with_tools.call_count == 3

        # Verify that memory accumulated the taboo lesson
        assert len(agent.memory.taboo_list) >= 1
        assert any("Encoding failure" in t or "Error" in t for t in agent.memory.taboo_list)

    def test_agent_handles_llm_self_reflection_dead_end(self, test_env):
        """Simulate LLM declaring DEAD_END -> Agent rolls back and switches."""
        workspace, staging_dir = test_env
        registry = ToolRegistry()

        def scan_dir(path: str):
            return ["empty_folder"]

        def fallback_search(keyword: str):
            return ["found_target.xlsx"]

        from jarvis.tools.system import backtrack
        registry.register(scan_dir)
        registry.register(fallback_search)
        registry.register(backtrack)

        mock_provider = MagicMock()
        mock_provider.chat_with_tools.side_effect = [
            # Turn 1: Scan
            AgentResponse(
                thought="폴더를 스캔합니다.",
                tool_calls=[ToolCall(name="scan_dir", args={"path": "."})],
                text=None,
            ),
            # Turn 2: LLM sees empty_folder and calls backtrack tool
            AgentResponse(
                thought="대상 파일이 없습니다. 직전 체크포인트로 롤백합니다.",
                tool_calls=[ToolCall(name="backtrack", args={"reason": "폴더가 비어있어 파일 탐색 불가능"})],
                text=None,
            ),
            # Turn 3: LLM executes fallback search
            AgentResponse(
                thought="전체 검색으로 선회합니다.",
                tool_calls=[ToolCall(name="fallback_search", args={"keyword": "target"})],
                text=None,
            ),
            # Turn 4: Completion
            AgentResponse(
                thought="완료 보고",
                tool_calls=[],
                text="최종 파일 target.xlsx 발견 완료",
            ),
        ]

        agent = JarvisAgent(
            provider=mock_provider,
            tool_registry=registry,
            max_turns=6,
            workspace_root=workspace,
        )

        result = agent.run("파일 찾아줘")
        assert "target.xlsx" in result
        assert any("비어있어" in t for t in agent.memory.taboo_list)
