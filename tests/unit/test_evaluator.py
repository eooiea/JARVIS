"""Unit tests for Universal Rule Evaluator, RetryBudgetManager, and HybridEvaluator (TDD)."""

import os
import tempfile
from pathlib import Path
import pytest

from jarvis.brain.evaluator import (
    UniversalRuleEvaluator,
    RetryBudgetManager,
    HybridEvaluator,
    EvaluationResult,
)


class TestUniversalRuleEvaluator:
    """Test suite for deterministic, tool-agnostic rule evaluation."""

    def test_infinite_loop_detection(self):
        evaluator = UniversalRuleEvaluator()
        tool_name = "read_file"
        args = {"path": "damaged.csv"}

        # 1st call passes rule check
        passed1, _ = evaluator.evaluate(tool_name, args, result="data line 1")
        assert passed1 is True

        # 2nd identical call fails as loop
        passed2, reason = evaluator.evaluate(tool_name, args, result="data line 1")
        assert passed2 is False
        assert "루프" in reason

    def test_error_and_exception_catching(self):
        evaluator = UniversalRuleEvaluator()

        # Exception object
        passed1, reason1 = evaluator.evaluate("scan_directory", {"path": "C:/"}, result=PermissionError("Access Denied"))
        assert passed1 is False
        assert "Access Denied" in reason1

        # Error string output
        passed2, reason2 = evaluator.evaluate("read_file", {"path": "missing.txt"}, result="Error: File not found")
        assert passed2 is False
        assert "Error:" in reason2

        # Error executing prefix from ToolRegistry
        passed3, reason3 = evaluator.evaluate("scan_directory", {"path": "missing"}, result="Error executing scan_directory: FileNotFoundError - [디렉터리를 찾을 수 없습니다]")
        assert passed3 is False
        assert "FileNotFoundError" in reason3

    def test_empty_result_detection(self):
        evaluator = UniversalRuleEvaluator()
        passed, reason = evaluator.evaluate("read_file", {"path": "empty.txt"}, result=None)
        assert passed is False
        assert "None" in reason or "빈 결과" in reason

    def test_file_creation_validation_success_and_zero_byte(self):
        evaluator = UniversalRuleEvaluator()
        temp_dir = tempfile.mkdtemp()

        # 1. Non-existent file
        missing_file = str(Path(temp_dir) / "not_created.xlsx")
        passed1, reason1 = evaluator.evaluate("create_excel", {"output_path": missing_file}, result="Done")
        assert passed1 is False
        assert "파일 생성 실패" in reason1 or "존재하지 않음" in reason1

        # 2. Zero-byte file
        zero_file = Path(temp_dir) / "zero.xlsx"
        zero_file.touch()
        passed2, reason2 = evaluator.evaluate("create_excel", {"output_path": str(zero_file)}, result="Done")
        assert passed2 is False
        assert "0바이트" in reason2

        # 3. Valid non-empty file
        valid_file = Path(temp_dir) / "valid.xlsx"
        valid_file.write_bytes(b"DATA123")
        passed3, _ = evaluator.evaluate("create_excel", {"output_path": str(valid_file)}, result="Done")
        assert passed3 is True

    def test_file_creation_validation_with_staging_dir(self):
        evaluator = UniversalRuleEvaluator()
        temp_dir = tempfile.mkdtemp()
        staging_dir = Path(temp_dir) / "staging"
        staging_dir.mkdir()

        # File created inside staging dir
        staged_file = staging_dir / "outputs" / "result.xlsx"
        staged_file.parent.mkdir(parents=True, exist_ok=True)
        staged_file.write_bytes(b"DATA123")

        passed, reason = evaluator.evaluate(
            "create_excel",
            {"output_path": "outputs/result.xlsx"},
            result="Done",
            staging_dir=staging_dir,
        )
        assert passed is True


class TestRetryBudgetManager:
    """Test suite for branch-level and total retry budget hard caps."""

    def test_branch_retry_budget_exceeded(self):
        mgr = RetryBudgetManager(max_retries_per_branch=2, total_retry_budget=5)
        phase = "SCAN"

        assert mgr.can_retry(phase) is True
        mgr.record_failure(phase)  # 1st failure

        assert mgr.can_retry(phase) is True
        mgr.record_failure(phase)  # 2nd failure

        # Exceeded branch limit of 2
        assert mgr.can_retry(phase) is False

    def test_total_retry_budget_exhausted(self):
        mgr = RetryBudgetManager(max_retries_per_branch=3, total_retry_budget=3)

        mgr.record_failure("PHASE_1")
        mgr.record_failure("PHASE_2")
        mgr.record_failure("PHASE_3")

        # Total 3 reached
        assert mgr.can_retry("PHASE_4") is False
        assert mgr.is_total_budget_exhausted() is True

    def test_reset_branch_on_success(self):
        mgr = RetryBudgetManager(max_retries_per_branch=2, total_retry_budget=5)
        mgr.record_failure("PHASE_1")
        assert mgr.get_branch_failures("PHASE_1") == 1

        mgr.reset_branch("PHASE_1")
        assert mgr.get_branch_failures("PHASE_1") == 0


class TestHybridEvaluator:
    """Test suite combining Rule Evaluator and LLM Self-Reflection."""

    def test_hybrid_passes_when_both_rule_and_reflection_are_good(self):
        hybrid = HybridEvaluator()
        result = hybrid.evaluate(
            tool_name="read_file",
            args={"path": "good.txt"},
            tool_result="Normal content",
            blackboard_delta={"status": "CONTINUE", "phase": "READ"},
        )
        assert result.passed is True
        assert result.is_dead_end is False

    def test_hybrid_fails_on_deterministic_rule_error(self):
        hybrid = HybridEvaluator()
        result = hybrid.evaluate(
            tool_name="read_file",
            args={"path": "broken.txt"},
            tool_result=FileNotFoundError("No such file"),
            blackboard_delta={"status": "CONTINUE"},
        )
        assert result.passed is False
        assert result.is_dead_end is False
        assert "No such file" in result.reason

    def test_hybrid_catches_llm_self_reflection_dead_end(self):
        hybrid = HybridEvaluator()
        result = hybrid.evaluate(
            tool_name="read_file",
            args={"path": "scanned.txt"},
            tool_result="Normal execution but contents are garbage",
            blackboard_delta={
                "status": "DEAD_END",
                "dead_end_reason": "인코딩 손상으로 복구 불가",
            },
        )
        assert result.passed is False
        assert result.is_dead_end is True
        assert "인코딩 손상" in result.reason
