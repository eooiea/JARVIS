"""Unit tests for JARVIS Session Logger (TDD Red-Green)."""

import pytest
from pathlib import Path
from jarvis.utils.session_logger import SessionLogger


def test_session_logger_creates_file(tmp_path: Path):
    """SessionLogger should create a new timestamped log file in the target directory."""
    logger = SessionLogger(log_dir=tmp_path, instruction="C:/test 폴더 정리")
    
    assert logger.log_file.exists()
    assert logger.log_file.suffix == ".md" or logger.log_file.suffix == ".log"
    assert "폴더_정리" in logger.log_file.name or "test" in logger.log_file.name


def test_session_logger_records_full_raw_events(tmp_path: Path):
    """SessionLogger should record turns, raw prompts, raw responses, thoughts, tool calls, and completion in exact layout."""
    logger = SessionLogger(log_dir=tmp_path, instruction="테스트 명령")

    logger.log_turn_start(turn=1)
    logger.log_llm_exchange(
        prompt="[System Prompt Full Text]\n[User]: Run scan",
        raw_response='{"thought": "스캔 시작", "tool_calls": [{"name": "scan_directory"}]}',
    )
    logger.log_thought(thought="스캔 시작")
    logger.log_tool_execution(
        tool_name="scan_directory",
        args={"path": "C:/demo", "recursive": True},
        result="[Result: 10 files found: a.txt, b.txt, c.txt]",
        duration_sec=0.12,
    )
    logger.log_completion(final_answer="작업이 무사히 완결되었습니다.")

    # Read back log file content
    content = logger.log_file.read_text(encoding="utf-8")

    assert "테스트 명령" in content
    assert "## 🔄 [Turn 1]" in content
    assert "### 📤 [LLM Input Prompt (Raw)]" in content
    assert "[System Prompt Full Text]" in content
    assert "### 📥 [LLM Output Response (Raw)]" in content
    assert "### 🧠 [Agent Thought]" in content
    assert "스캔 시작" in content
    assert "### 🛠️ [Tool Execution: `scan_directory`]" in content
    assert "C:/demo" in content
    assert "10 files found" in content
    assert "## 🏁 [Task Final Completion]" in content
    assert "작업이 무사히 완결되었습니다" in content

    # Verify exact sequential ordering
    idx_turn = content.index("## 🔄 [Turn 1]")
    idx_prompt = content.index("### 📤 [LLM Input Prompt (Raw)]")
    idx_resp = content.index("### 📥 [LLM Output Response (Raw)]")
    idx_thought = content.index("### 🧠 [Agent Thought]")
    idx_tool = content.index("### 🛠️ [Tool Execution: `scan_directory`]")
    idx_comp = content.index("## 🏁 [Task Final Completion]")

    assert idx_turn < idx_prompt < idx_resp < idx_thought < idx_tool < idx_comp


def test_session_logger_unique_filenames_per_session(tmp_path: Path):
    """Multiple sessions started rapidly with same instruction must not overwrite each other."""
    logger1 = SessionLogger(log_dir=tmp_path, instruction="동일한 작업 지시")
    logger2 = SessionLogger(log_dir=tmp_path, instruction="동일한 작업 지시")

    assert logger1.log_file != logger2.log_file
    assert logger1.log_file.exists()
    assert logger2.log_file.exists()


def test_session_logger_records_thought_and_backtracking(tmp_path: Path):
    """SessionLogger should record clean thoughts, tool traces, and backtracking rollbacks."""
    logger = SessionLogger(log_dir=tmp_path, instruction="장애 복구 테스트")

    logger.log_turn_start(turn=1)
    logger.log_thought(thought="README.md를 먼저 탐색합니다.")
    logger.log_backtracking(
        reason="파일이 존재하지 않아 대안 경로로 롤백합니다.",
        rollback_turn=0,
        taboo_list=["실패: 존재하지않는파일_9999.txt 접근 시도 금지"],
    )

    content = logger.log_file.read_text(encoding="utf-8")
    assert "README.md를 먼저 탐색합니다." in content
    assert "### 🧠 [Agent Thought]" in content
    assert "롤백" in content or "Backtracking" in content
    assert "존재하지않는파일_9999.txt 접근 시도 금지" in content


