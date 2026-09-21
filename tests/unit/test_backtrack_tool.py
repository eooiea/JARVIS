"""Unit test for backtrack tool integration in JARVIS ReAct loop."""

import pytest
from unittest.mock import MagicMock
from jarvis.brain.agent import JarvisAgent
from jarvis.providers.base import AgentResponse, ToolCall
from jarvis.brain.checkpoint import CheckpointManager
from jarvis.brain.evaluator import HybridEvaluator
from jarvis.brain.memory import WorkingMemory, Milestone
from jarvis.infra.staging import ShadowWorkspace
from jarvis.tools.registry import ToolRegistry


def test_backtrack_tool_triggers_rollback_and_accumulates_taboo(tmp_path):
    """LLM이 backtrack 도구를 호출했을 때, 직전 체크포인트로 정상 롤백되고 Taboo List가 갱신되어야 한다."""
    registry = ToolRegistry()

    # 가상의 도구들 등록
    def dummy_read(path: str) -> str:
        """Read dummy file."""
        return "content"

    def dummy_backtrack(reason: str) -> dict:
        """Backtrack tool."""
        return {"status": "BACKTRACK_TRIGGERED", "reason": reason}

    registry.register(dummy_read, name="read_file")
    registry.register(dummy_backtrack, name="backtrack")

    # Mock Provider:
    # Turn 1: LLM이 dummy_read 도구를 호출하여 첫 번째 체크포인트 생성
    # Turn 2: LLM이 막다른 길임을 인지하고 backtrack(reason="데이터 깨짐 발견") 도구를 호출
    # Turn 3: 롤백 후 대안을 실행하여 최종 완결 텍스트 출력
    mock_provider = MagicMock()

    turn1_resp = AgentResponse(
        thought="1단계로 파일을 읽어보겠습니다.",
        blackboard_delta={"phase": "PROCESS"},
        tool_calls=[ToolCall(name="read_file", args={"path": "orders/a.xlsx"})],
        clean_text="",
    )

    turn2_resp = AgentResponse(
        thought="데이터가 예상과 달라 더 이상 진행이 불가능합니다. 이전 단계로 롤백합니다.",
        blackboard_delta={},
        tool_calls=[ToolCall(name="backtrack", args={"reason": "a.xlsx 데이터 컬럼 심각한 훼손"})],
        clean_text="",
    )

    turn3_resp = AgentResponse(
        thought="롤백 후 Taboo List를 확인하고 대안으로 완결했습니다.",
        blackboard_delta={"phase": "COMPLETE"},
        tool_calls=[],
        text="작업이 대안 경로를 통해 완벽히 완료되었습니다.",
    )

    mock_provider.chat_with_tools.side_effect = [turn1_resp, turn2_resp, turn3_resp]

    workspace_dir = tmp_path / "workspace"
    workspace_dir.mkdir()
    staging = ShadowWorkspace(task_id="test_bt", staging_base_dir=str(tmp_path / "staging"))
    cp_mgr = CheckpointManager(session_id="test_bt", storage_dir=tmp_path / "checkpoints")

    agent = JarvisAgent(
        provider=mock_provider,
        tool_registry=registry,
        max_turns=5,
        workspace_root=str(workspace_dir),
        staging=staging,
        checkpoint_manager=cp_mgr,
    )

    result = agent.run("주문서 처리해줘")

    # 검증:
    # 1. 3번째 턴에서 최종 완료 텍스트가 정상 반환되어야 함
    assert "완벽히 완료되었습니다" in result

    # 2. agent의 WorkingMemory Taboo List에 backtrack의 reason이 누적되어 있어야 함
    assert any("a.xlsx 데이터 컬럼 심각한 훼손" in t for t in agent.memory.taboo_list)

    # 3. Provider가 총 3회 호출되어야 함 (Turn 1 -> Turn 2(롤백) -> Turn 3(완결))
    assert mock_provider.chat_with_tools.call_count == 3


def test_backtrack_tool_budget_exhaustion_aborts_safely(tmp_path):
    """backtrack 도구를 반복 호출하여 예산(Branch 2회)을 초과하면 안전하게 작업을 중단해야 한다."""
    registry = ToolRegistry()

    def dummy_backtrack(reason: str) -> dict:
        return {"status": "BACKTRACK_TRIGGERED", "reason": reason}

    registry.register(dummy_backtrack, name="backtrack")

    mock_provider = MagicMock()
    bt_resp = AgentResponse(
        thought="지속적으로 막다른 길입니다.",
        blackboard_delta={},
        tool_calls=[ToolCall(name="backtrack", args={"reason": "연속 실패"})],
        text="",
    )
    mock_provider.chat_with_tools.return_value = bt_resp

    staging = ShadowWorkspace(task_id="test_bt_budget", staging_base_dir=str(tmp_path / "staging"))
    cp_mgr = CheckpointManager(session_id="test_bt_budget", storage_dir=tmp_path / "checkpoints")

    agent = JarvisAgent(
        provider=mock_provider,
        tool_registry=registry,
        max_turns=5,
        workspace_root=str(tmp_path),
        staging=staging,
        checkpoint_manager=cp_mgr,
    )

    result = agent.run("불가능한 작업")
    assert "재시도 한도 초과" in result or "재시도 예산 초과" in result


def test_backtrack_tool_schema_registration():
    """ToolRegistry에 backtrack 도구가 정상 등록되고 스키마가 생성되는지 검증."""
    from jarvis.tools.system import backtrack

    registry = ToolRegistry()
    registry.register(backtrack, name="backtrack")

    schemas = registry.get_definitions()
    assert len(schemas) == 1
    schema = schemas[0]
    assert schema["name"] == "backtrack"
    assert "reason" in schema["parameters"]["properties"]
    assert "reason" in schema["parameters"]["required"]

