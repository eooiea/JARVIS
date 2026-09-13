"""Integration test for Scenario A: Autonomous LLM Tool-Calling for Directory Scan to Excel."""

import pytest
import openpyxl
from pathlib import Path
from unittest.mock import MagicMock
from jarvis.main import JarvisPipeline
from jarvis.providers.base import AgentResponse, ToolCall


def test_scenario_a_scan_directory_to_excel(tmp_path: Path):
    """Scenario A: LLM Brain autonomously calls scan_directory and create_excel."""
    test_dir = tmp_path / "my_project"
    test_dir.mkdir()
    (test_dir / "src").mkdir()
    (test_dir / "src" / "main.py").write_text("print('hello')", encoding="utf-8")
    (test_dir / "README.md").write_text("# Project", encoding="utf-8")

    out_dir = tmp_path / "outputs"
    target_excel = out_dir / "my_project_폴더구조.xlsx"

    # Mock Provider behaving like Gemini Brain
    mock_provider = MagicMock()
    mock_provider.chat_with_tools.side_effect = [
        # Turn 1: LLM decides to scan directory
        AgentResponse(
            thought="폴더 구조를 먼저 스캔하기 위해 scan_directory 도구를 호출한다.",
            tool_calls=[ToolCall(name="scan_directory", args={"path": str(test_dir), "recursive": True})],
            text=None,
        ),
        # Turn 2: LLM sees scanned items and decides to create styled Excel
        AgentResponse(
            thought="스캔된 결과를 바탕으로 create_excel 도구를 호출한다.",
            tool_calls=[ToolCall(name="create_excel", args={
                "data": [
                    {"name": "src", "type": "폴더", "size": "1개 항목"},
                    {"name": "main.py", "type": "파일", "size": "14 B"},
                    {"name": "README.md", "type": "파일", "size": "9 B"},
                ],
                "output_path": str(target_excel),
                "sheet_name": "폴더구조",
            })],
            text=None,
        ),
        # Turn 3: LLM final answer
        AgentResponse(
            thought="작업이 모두 완료되었으므로 사용자에게 보고한다.",
            tool_calls=[],
            text="폴더 구조 엑셀 파일이 성공적으로 생성되었습니다.",
        ),
    ]

    pipeline = JarvisPipeline(provider=mock_provider, output_dir=out_dir)

    instruction = f"{test_dir} 안의 폴더구조를 엑셀로 정리해줘"
    result = pipeline.execute_instruction(instruction=instruction, auto_confirm=True)

    assert result["success"] is True
    assert "성공적으로 생성되었습니다" in result["report"]
    assert target_excel.exists()

    # Verify that Excel contains real rows
    wb = openpyxl.load_workbook(target_excel)
    ws = wb.active
    assert ws is not None
    assert ws.max_row == 4  # Header + 3 rows
    assert mock_provider.chat_with_tools.call_count == 3
