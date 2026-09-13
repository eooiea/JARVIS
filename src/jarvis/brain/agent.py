"""Autonomous ReAct Agent with Working Memory, Blackboard, and Backtracking Engine."""

import os
import time
from typing import Any, Dict, List, Optional

from jarvis.brain.checkpoint import CheckpointManager
from jarvis.brain.evaluator import HybridEvaluator
from jarvis.brain.memory import (
    BlackboardOutputParser,
    Milestone,
    PromptBuilder,
    WorkingMemory,
    apply_blackboard_delta,
    render_blackboard,
)
from jarvis.infra.staging import ShadowWorkspace
from jarvis.providers.base import AgentResponse, ToolCall
from jarvis.tools.registry import ToolRegistry
from jarvis.utils.logger import get_logger
from jarvis.utils.session_logger import SessionLogger

logger = get_logger("brain.agent")


class JarvisAgent:
    """True Autonomous Agent with Stateful Blackboard Working Memory and Backtracking Engine."""

    def __init__(
        self,
        provider: Any,
        tool_registry: ToolRegistry,
        max_turns: int = 8,
        session_logger: Optional[SessionLogger] = None,
        workspace_root: Optional[str] = None,
        task_id: Optional[str] = None,
        evaluator: Optional[HybridEvaluator] = None,
        checkpoint_manager: Optional[CheckpointManager] = None,
        staging: Optional[ShadowWorkspace] = None,
    ):
        self.provider = provider
        self.registry = tool_registry
        self.max_turns = max_turns
        self.session_logger = session_logger
        self.workspace_root = workspace_root
        self.task_id = task_id
        self.evaluator = evaluator
        self.checkpoint_manager = checkpoint_manager
        self.staging = staging
        self.memory: Optional[WorkingMemory] = None

    def run(self, instruction: str) -> str:
        """Run autonomous ReAct loop with blackboard updates, staging, evaluation, and rollback."""
        logger.info(f"Agent starting autonomous run for: '{instruction}'")
        task_id = self.task_id or f"task_{int(time.time() * 1000)}"

        # 1. Initialize Working Memory, Staging, Checkpointer, Evaluator
        self.memory = WorkingMemory(main_goal=instruction)
        if not self.memory.milestones:
            self.memory.milestones = [
                Milestone(id=1, title="작업 대상 탐색 및 데이터 수집", status="IN_PROGRESS"),
                Milestone(id=2, title="데이터 가공 및 도구 실행", status="PENDING"),
                Milestone(id=3, title="최종 결과 검증 및 완결 보고", status="PENDING"),
            ]
        staging = self.staging or ShadowWorkspace(task_id=task_id)
        cp_mgr = self.checkpoint_manager or CheckpointManager(session_id=task_id)
        evaluator = self.evaluator or HybridEvaluator()

        system_prompt = (
            "당신은 Windows 환경에서 사용자의 모든 작업을 자율적으로 보조하고 완결짓는 초지능 데스크톱 어시스턴트 JARVIS입니다.\n"
            "사용자의 명령을 달성하기 위해 주어진 도구(Tools)들을 신중하고 정확하게 선택하여 순차적으로 실행하십시오.\n\n"
            "[출력 형식 필수 규칙]\n"
            "당신은 매 턴 반드시 아래의 2개 XML 태그를 먼저 작성한 뒤 도구를 호출하거나 최종 답변을 출력해야 합니다:\n"
            "1. <thought>: 현재 상황 분석, 가설 검증 결과, 다음 액션 근거 (2~3문장)\n"
            "2. <blackboard>: 작업 칠판 업데이트 내용 (YAML 포맷)\n"
            "   - phase: 현재 단계명\n"
            "   - update_milestones: [{id: 1, status: 'DONE'}, ...] (상태 변경 시만)\n"
            "   - add_findings: {key: value} (새로운 발견 데이터)\n"
            "   - status: 'CONTINUE' 또는 막다른 길일 경우 'DEAD_END'\n"
            "   - dead_end_reason: '막다른 길인 구체적 이유' (status가 DEAD_END일 때만)\n\n"
            "[금지 규칙 및 백트래킹 원칙]\n"
            "작업 칠판의 Taboo List에 기재된 실패 내역은 이미 실패가 확인된 경로입니다. 절대로 Taboo List의 인자나 도구를 재호출하지 말고 즉시 대안 계획이나 다른 경로를 수행하십시오.\n\n"
            "작업이 성공적으로 완결되면 사용자에게 최종 요약 보고를 제시하고 종료하십시오."
        )

        prompt_builder = PromptBuilder(
            system_instruction=system_prompt,
            tool_schemas=self.registry.get_definitions(),
        )

        messages: List[Dict[str, Any]] = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": instruction},
        ]

        # Save initial safe checkpoint (Turn 0)
        cp_mgr.save_checkpoint(
            memory=self.memory,
            message_index=len(messages),
            phase="INIT",
            description="작업 시작 초기점",
            turn=0,
        )

        for turn in range(1, self.max_turns + 1):
            logger.info(f"--- [Turn {turn}/{self.max_turns}] LLM Brain Thinking (Phase: {self.memory.current_phase}) ---")
            if self.session_logger:
                self.session_logger.log_turn_start(turn=turn)

            # Re-render dynamic blackboard (including updated milestones and taboo list)
            messages[0]["content"] = f"{system_prompt}\n\n{render_blackboard(self.memory)}"

            tool_schemas = self.registry.get_definitions()
            response: AgentResponse = self.provider.chat_with_tools(messages, tools=tool_schemas)

            # Dual output parsing
            raw_text = (response.thought or "") + "\n" + (response.text or "")
            parsed = BlackboardOutputParser.parse(raw_text)

            thought = response.thought or parsed["thought"]
            blackboard_delta = response.blackboard_delta or parsed["blackboard_delta"]
            clean_text = parsed["clean_text"] or response.text

            # Apply blackboard delta
            apply_blackboard_delta(self.memory, blackboard_delta)

            if thought:
                logger.info(f"🧠 Thought: {thought}")
                if self.session_logger:
                    self.session_logger.log_thought(
                        thought=thought,
                        raw_blackboard=render_blackboard(self.memory),
                    )

            # Check if LLM self-reflection declared DEAD_END without tools
            if blackboard_delta.get("status") == "DEAD_END":
                dead_end_reason = blackboard_delta.get("dead_end_reason") or "LLM 스스로 막다른 길(DEAD_END) 선언"
                logger.warning(f"Self-reflection DEAD_END declared: {dead_end_reason}")
                evaluator.budget_manager.record_failure(self.memory.current_phase)

                if not evaluator.budget_manager.can_retry(self.memory.current_phase):
                    abort_msg = f"작업 중단: {self.memory.current_phase} 단계에서 재시도 예산 초과 ({dead_end_reason})"
                    logger.error(abort_msg)
                    if self.session_logger:
                        self.session_logger.log_completion(final_answer=abort_msg)
                    return abort_msg

                # Rollback
                staging.discard()
                restored_mem, prune_idx = cp_mgr.rollback_to(failure_reason=dead_end_reason)
                self.memory = restored_mem
                messages = messages[:prune_idx]
                evaluator.rule_evaluator.last_call = None
                if self.session_logger:
                    rb_turn = cp_mgr.history[-1].turn if cp_mgr.history else 0
                    self.session_logger.log_backtracking(
                        reason=dead_end_reason,
                        rollback_turn=rb_turn,
                        taboo_list=self.memory.taboo_list,
                    )
                continue

            # If LLM requested tool execution
            if response.tool_calls:
                should_rollback = False
                for tc in response.tool_calls:
                    logger.info(f"🛠️ Action: Call Tool '{tc.name}' with args {tc.args}")
                    t_start = time.time()

                    # Execute write/mutation tools in isolated staging, read tools in workspace context
                    if tc.name.startswith(("create_", "write_", "export_", "save_")):
                        with staging.in_staging():
                            obs = self.registry.execute(tc.name, **tc.args)
                    else:
                        obs = self.registry.execute(tc.name, **tc.args)
                    duration_sec = time.time() - t_start

                    obs_str = str(obs)
                    logger.info(f"👁️ Observation from '{tc.name}': {obs_str[:150]}...")

                    if self.session_logger:
                        self.session_logger.log_tool_execution(
                            tool_name=tc.name,
                            args=tc.args,
                            result=obs_str,
                            duration_sec=duration_sec,
                        )

                    # Hybrid evaluation
                    eval_res = evaluator.evaluate(
                        tool_name=tc.name,
                        args=tc.args,
                        tool_result=obs,
                        blackboard_delta=blackboard_delta,
                        staging_dir=staging.staging_dir,
                    )

                    if eval_res.passed:
                        # Success: Commit to real workspace and save new checkpoint
                        target_ws = self.workspace_root or os.getcwd()
                        committed = staging.commit_to_workspace(target_workspace=target_ws)

                        messages.append({
                            "role": "assistant",
                            "content": thought or "",
                            "tool_calls": [{"name": tc.name, "args": tc.args}],
                        })
                        messages.append({
                            "role": "tool",
                            "name": tc.name,
                            "content": obs_str,
                        })

                        # Auto-advance blackboard state upon tool success
                        if tc.name.startswith(("scan_", "read_", "search_", "find_")):
                            self.memory.current_phase = "PROCESS"
                            if len(self.memory.milestones) >= 2:
                                self.memory.milestones[0].status = "DONE"
                                self.memory.milestones[1].status = "IN_PROGRESS"
                            self.memory.key_findings[f"{tc.name}_관측"] = f"성공 ({str(obs)[:60]}...)"
                        elif tc.name.startswith(("create_", "write_", "export_", "save_")):
                            self.memory.current_phase = "VERIFY"
                            if len(self.memory.milestones) >= 3:
                                self.memory.milestones[1].status = "DONE"
                                self.memory.milestones[2].status = "IN_PROGRESS"
                            out_p = tc.args.get("output_path") or tc.args.get("path") or "완료 파일"
                            self.memory.key_findings[f"{tc.name}_생성"] = f"{out_p} 파일 생성 성공"

                        cp_mgr.save_checkpoint(
                            memory=self.memory,
                            message_index=len(messages),
                            phase=self.memory.current_phase,
                            description=f"도구 '{tc.name}' 실행 성공",
                            committed_artifacts=committed,
                            turn=turn,
                        )
                        evaluator.budget_manager.reset_branch(self.memory.current_phase)
                    else:
                        # Failure or Dead End: trigger backtracking
                        logger.warning(f"Evaluation Failed on tool '{tc.name}': {eval_res.reason}")
                        evaluator.budget_manager.record_failure(self.memory.current_phase)

                        if not evaluator.budget_manager.can_retry(self.memory.current_phase):
                            abort_msg = f"작업 중단: {self.memory.current_phase} 단계에서 재시도 한도 초과 ({eval_res.reason})"
                            logger.error(abort_msg)
                            if self.session_logger:
                                self.session_logger.log_completion(final_answer=abort_msg)
                            return abort_msg

                        staging.discard()
                        restored_mem, prune_idx = cp_mgr.rollback_to(failure_reason=eval_res.reason)
                        self.memory = restored_mem
                        messages = messages[:prune_idx]
                        evaluator.rule_evaluator.last_call = None
                        if self.session_logger:
                            rb_turn = cp_mgr.history[-1].turn if cp_mgr.history else 0
                            self.session_logger.log_backtracking(
                                reason=eval_res.reason,
                                rollback_turn=rb_turn,
                                taboo_list=self.memory.taboo_list,
                            )
                        should_rollback = True
                        break

                if should_rollback:
                    continue

            else:
                # No tool calls: LLM finished the task
                logger.info("Task completed by LLM Brain.")
                target_ws = self.workspace_root or os.getcwd()
                staging.commit_to_workspace(target_workspace=target_ws)

                self.memory.current_phase = "COMPLETE"
                if self.memory.milestones:
                    for m in self.memory.milestones:
                        m.status = "DONE"

                final_text = clean_text or "작업이 성공적으로 완료되었습니다."
                if self.session_logger:
                    self.session_logger.log_completion(final_answer=final_text)
                return final_text

        warning_msg = f"에이전트가 최대 실행 횟수({self.max_turns}회)에 도달하여 작업을 중단했습니다."
        logger.warning(warning_msg)
        if self.session_logger:
            self.session_logger.log_completion(final_answer=warning_msg)
        return warning_msg
