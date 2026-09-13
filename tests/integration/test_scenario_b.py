"""Integration test for Scenario B: Autonomous LLM Tool-Calling for Batch Receipts to Excel."""

import pytest
import openpyxl
from pathlib import Path
from unittest.mock import MagicMock
from jarvis.main import JarvisPipeline
from jarvis.providers.base import AgentResponse, ToolCall


def test_scenario_b_batch_receipts_to_excel(tmp_path: Path):
    """Scenario B: LLM Brain autonomously scans receipt files, batch analyzes them, and creates merged Excel."""
    receipts_dir = tmp_path / "receipts_folder"
    receipts_dir.mkdir()

    r1 = receipts_dir / "receipt1.png"
    r2 = receipts_dir / "receipt2.png"
    r1.write_bytes(b"\x89PNG dummy1")
    r2.write_bytes(b"\x89PNG dummy2")

    out_dir = tmp_path / "outputs"
    target_excel = out_dir / "영수증_종합_정산.xlsx"

    # Mock Provider
    mock_provider = MagicMock()
    mock_provider.chat_with_tools.side_effect = [
        # Turn 1: LLM scans folder
        AgentResponse(
            thought="영수증 파일들을 찾기 위해 scan_directory를 호출한다.",
            tool_calls=[ToolCall(name="scan_directory", args={"path": str(receipts_dir), "recursive": False})],
            text=None,
        ),
        # Turn 2: LLM batch analyzes receipts
        AgentResponse(
            thought="발견된 2개의 영수증에 대해 batch_analyze_documents를 호출한다.",
            tool_calls=[ToolCall(name="batch_analyze_documents", args={"file_paths": [str(r1), str(r2)]})],
            text=None,
        ),
        # Turn 3: LLM creates merged Excel
        AgentResponse(
            thought="분석된 영수증 데이터를 통합 엑셀로 저장한다.",
            tool_calls=[ToolCall(name="create_excel", args={
                "data": [
                    {"상호명": "스타벅스", "품목": "아메리카노", "금액": 4500},
                    {"상호명": "맥도날드", "품목": "빅맥세트", "금액": 7200},
                ],
                "output_path": str(target_excel),
                "sheet_name": "영수증정산",
            })],
            text=None,
        ),
        # Turn 4: Final answer
        AgentResponse(
            thought="완결 보고",
            tool_calls=[],
            text="영수증 2건을 분석하여 엑셀 파일 생성을 완료했습니다.",
        ),
    ]

    pipeline = JarvisPipeline(provider=mock_provider, output_dir=out_dir)

    instruction = f"{receipts_dir} 폴더에 있는 영수증들 전부 보고 엑셀로 만들어줘"
    result = pipeline.execute_instruction(instruction=instruction, auto_confirm=True)

    assert result["success"] is True
    assert target_excel.exists()

    # Verify merged Excel
    wb = openpyxl.load_workbook(target_excel)
    ws = wb.active
    assert ws.max_row == 3  # Header + 2 receipts
    assert mock_provider.chat_with_tools.call_count == 4
