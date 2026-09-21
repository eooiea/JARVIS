"""Hybrid Evaluator: Deterministic Rule Evaluator and LLM Self-Reflection with Retry Budget."""

import os
from pathlib import Path
from typing import Any, Dict, Optional, Tuple
from pydantic import BaseModel, Field

from jarvis.utils.logger import get_logger

logger = get_logger("brain.evaluator")


class EvaluationResult(BaseModel):
    """Result of hybrid evaluation."""
    passed: bool
    reason: str
    is_dead_end: bool = False


class UniversalRuleEvaluator:
    """Tool-agnostic deterministic rule evaluator (0ms / Zero-cost)."""

    def __init__(self):
        self.last_call: Optional[Tuple[str, str]] = None

    def evaluate(
        self,
        tool_name: str,
        args: Dict[str, Any],
        result: Any,
        staging_dir: Optional[Any] = None,
    ) -> Tuple[bool, str]:
        """Evaluate deterministic facts: loops, exceptions, empty outputs, and file creation."""
        # 1. Infinite loop breaker
        call_signature = (tool_name, str(sorted(args.items())))
        if self.last_call == call_signature:
            logger.warning(f"Detected duplicate execution loop for tool '{tool_name}' with args {args}")
            return False, f"동일한 인자로 '{tool_name}' 연속 반복 호출(루프) 감지"
        self.last_call = call_signature

        # 2. Exception or error catching
        if isinstance(result, Exception):
            err_msg = f"도구 실행 중 예외 발생: {type(result).__name__} - {str(result)}"
            logger.warning(err_msg)
            return False, err_msg

        if isinstance(result, str) and (result.startswith("Error:") or result.startswith("Error executing") or result.startswith("Validation Error:")):
            logger.warning(f"Tool returned error string: {result}")
            return False, result

        # 3. Empty result guard
        if result is None or (isinstance(result, str) and not result.strip()):
            logger.warning(f"Tool '{tool_name}' returned empty or None result")
            return False, f"도구 '{tool_name}'의 실행 결과가 None 또는 빈 결과입니다."

        # 4. File creation category rules
        if tool_name.startswith(("create_", "write_", "export_")) or "output_path" in args:
            target_path = args.get("output_path") or args.get("path")
            if target_path:
                p = Path(target_path)
                # If staging is active, check staging directory
                if staging_dir:
                    staged_path = Path(staging_dir) / target_path
                    if staged_path.exists():
                        p = staged_path
                    elif p.is_absolute():
                        try:
                            rel = p.relative_to(Path.cwd())
                            cand = Path(staging_dir) / rel
                            if cand.exists():
                                p = cand
                        except ValueError:
                            cand = Path(staging_dir) / p.name
                            if cand.exists():
                                p = cand

                if not p.exists():
                    msg = f"파일 생성 실패: 경로 '{target_path}'에 파일이 존재하지 않음"
                    logger.warning(msg)
                    return False, msg

                if p.stat().st_size == 0:
                    msg = f"파일 생성 실패: 생성된 파일이 0바이트 빈 파일임 ('{target_path}')"
                    logger.warning(msg)
                    return False, msg

        return True, "PASS"


class RetryBudgetManager:
    """Tracks and enforces retry budget per milestone branch and total task."""

    def __init__(self, max_retries_per_branch: int = 2, total_retry_budget: int = 5):
        self.max_retries_per_branch = max_retries_per_branch
        self.total_retry_budget = total_retry_budget
        self.branch_failures: Dict[str, int] = {}
        self.total_failures: int = 0

    def record_failure(self, phase: str) -> None:
        """Record a failure for the specified phase/branch."""
        self.branch_failures[phase] = self.branch_failures.get(phase, 0) + 1
        self.total_failures += 1
        logger.info(
            f"Recorded failure for phase '{phase}'. "
            f"Branch count: {self.branch_failures[phase]}/{self.max_retries_per_branch}, "
            f"Total count: {self.total_failures}/{self.total_retry_budget}"
        )

    def can_retry(self, phase: str) -> bool:
        """Check if retrying is allowed for the phase within budget limits."""
        if self.total_failures >= self.total_retry_budget:
            return False
        if self.branch_failures.get(phase, 0) >= self.max_retries_per_branch:
            return False
        return True

    def is_total_budget_exhausted(self) -> bool:
        """Check if overall task retry budget is exhausted."""
        return self.total_failures >= self.total_retry_budget

    def reset_branch(self, phase: str) -> None:
        """Reset branch failure counter on milestone pass."""
        if phase in self.branch_failures:
            self.branch_failures[phase] = 0

    def get_branch_failures(self, phase: str) -> int:
        """Get failure count for a specific branch."""
        return self.branch_failures.get(phase, 0)


class HybridEvaluator:
    """Combines deterministic rule checks with LLM self-reflection and retry budgeting."""

    def __init__(
        self,
        rule_evaluator: Optional[UniversalRuleEvaluator] = None,
        budget_manager: Optional[RetryBudgetManager] = None,
    ):
        self.rule_evaluator = rule_evaluator or UniversalRuleEvaluator()
        self.budget_manager = budget_manager or RetryBudgetManager()

    def evaluate(
        self,
        tool_name: str,
        args: Dict[str, Any],
        tool_result: Any,
        blackboard_delta: Optional[Dict[str, Any]] = None,
        staging_dir: Optional[Any] = None,
    ) -> EvaluationResult:
        """Run deterministic rules to evaluate tool execution validity."""
        passed, reason = self.rule_evaluator.evaluate(
            tool_name, args, tool_result, staging_dir=staging_dir
        )
        if not passed:
            return EvaluationResult(passed=False, reason=reason, is_dead_end=False)

        return EvaluationResult(passed=True, reason="PASS", is_dead_end=False)
