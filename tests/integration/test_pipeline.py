"""Integration tests for JARVIS End-to-End Autonomous ReAct Pipeline (TDD Red-Green)."""

import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch
from jarvis.main import JarvisPipeline
from jarvis.providers.base import AgentResponse, ToolCall


def test_pipeline_end_to_end_vision_to_excel(tmp_path: Path):
    """End-to-End test: User instruction -> LLM calls capture_screen -> LLM calls create_excel -> Report."""
    out_dir = tmp_path / "outputs"
    target_excel = out_dir / "화면_영수증_정리.xlsx"

    mock_provider = MagicMock()
    mock_provider.chat_with_tools.side_effect = [
        # Turn 1: LLM calls capture_screen
        AgentResponse(
            thought="화면 속 영수증을 확인하기 위해 capture_screen 도구를 호출한다.",
            tool_calls=[ToolCall(name="capture_screen", args={})],
            text=None,
        ),
        # Turn 2: LLM calls create_excel
        AgentResponse(
            thought="영수증 항목을 엑셀로 저장하기 위해 create_excel 도구를 호출한다.",
            tool_calls=[ToolCall(name="create_excel", args={
                "data": [
                    {"품목": "제육볶음", "금액": 10000, "수량": 2},
                    {"품목": "공기밥", "금액": 1000, "수량": 2},
                ],
                "output_path": str(target_excel),
                "sheet_name": "영수증",
            })],
            text=None,
        ),
        # Turn 3: LLM finishes
        AgentResponse(
            thought="완료 보고를 작성한다.",
            tool_calls=[],
            text="화면 속 영수증을 엑셀 파일로 완벽하게 정리했습니다.",
        ),
    ]

    pipeline = JarvisPipeline(
        provider=mock_provider,
        output_dir=out_dir,
    )

    with patch("jarvis.tools.vision.capture_screen", return_value=b"\x89PNG dummy"):
        result = pipeline.execute_instruction(
            instruction="화면 영수증을 캡처해서 엑셀로 만들어줘",
            auto_confirm=True,
        )

    assert result["success"] is True
    assert "영수증을 엑셀 파일로 완벽하게 정리했습니다" in result["report"]
    assert target_excel.exists()
    assert mock_provider.chat_with_tools.call_count == 3
