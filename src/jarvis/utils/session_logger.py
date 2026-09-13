"""Full-fidelity Session Logger for recording agent turns, raw LLM exchanges, and tool traces."""

import re
import json
import time
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any, Union


class SessionLogger:
    """Records complete raw execution history into a dedicated session markdown file."""

    def __init__(
        self,
        instruction: str,
        log_dir: Optional[Union[str, Path]] = None,
        session_id: Optional[str] = None,
    ):
        self.instruction = instruction
        self.start_time = time.time()
        now = datetime.now()
        timestamp_str = now.strftime("%Y%m%d_%H%M%S")
        ms_str = f"{int(now.microsecond / 1000):03d}"
        self.session_id = session_id or f"{timestamp_str}_{ms_str}"

        target_dir = Path(log_dir).resolve() if log_dir else Path.cwd() / "logs"
        target_dir.mkdir(parents=True, exist_ok=True)

        # Sanitize instruction snippet for filename
        clean_name = re.sub(r'[^\w가-힣]', '_', instruction.strip())
        clean_name = re.sub(r'_+', '_', clean_name).strip('_')[:40] or "task"
        
        base_name = f"{timestamp_str}_{ms_str}_{clean_name}"
        filename = f"{base_name}.md"
        counter = 1
        while (target_dir / filename).exists():
            filename = f"{base_name}_{counter}.md"
            counter += 1

        self.log_file = target_dir / filename

        # Write initial session header
        initial_header = (
            f"# 📋 JARVIS Execution Trace Log\n\n"
            f"- **Session ID**: `{self.session_id}`\n"
            f"- **Start Time**: {now.strftime('%Y-%m-%d %H:%M:%S')}\n"
            f"- **User Instruction**: `{instruction}`\n\n"
            f"---\n"
        )
        self._append(initial_header)

    def _append(self, text: str):
        """Append text to log file with immediate disk flush."""
        with open(self.log_file, "a", encoding="utf-8") as f:
            f.write(text + "\n")
            f.flush()

    def log_turn_start(self, turn: int):
        """Record beginning of a new ReAct turn."""
        block = (
            f"\n## 🔄 [Turn {turn}]\n"
            f"*Timestamp: {datetime.now().strftime('%H:%M:%S')}*\n"
        )
        self._append(block)

    def log_thought(
        self,
        thought: str,
        raw_blackboard: Optional[str] = None,
        phase: Optional[str] = None,
        milestones: Optional[list] = None,
        key_findings: Optional[Dict[str, Any]] = None,
        taboo_list: Optional[list] = None,
    ):
        """Record agent's reasoning and the exact raw injected blackboard state."""
        lines = []
        if raw_blackboard:
            fence = "````"
            while fence in raw_blackboard:
                fence += "`"
            lines.append("### 📋 [주입된 작업 칠판 원문 (Injected Raw Blackboard)]")
            lines.append(f"{fence}text\n{raw_blackboard.strip()}\n{fence}")
        else:
            lines.append("### 📋 [작업 칠판 (Working Blackboard)]")
            lines.append(f"- **현재 단계 (Phase)**: `{phase or 'INIT'}`")

            lines.append("- **마일스톤 진행 현황 (Milestones)**:")
            if milestones:
                for m in milestones:
                    lines.append(f"  - {m}")
            else:
                lines.append("  - (등록된 마일스톤 없음)")

            lines.append("- **핵심 발견 사항 (Key Findings)**:")
            if key_findings:
                for k, v in key_findings.items():
                    lines.append(f"  - `{k}`: {v}")
            else:
                lines.append("  - (수집된 발견 사항 없음)")

            lines.append("- **금지 규칙 (Taboo List)**:")
            if taboo_list:
                for t in taboo_list:
                    lines.append(f"  - 🚫 {t}")
            else:
                lines.append("  - (없음)")

        lines.append(f"\n> 💭 **AI 판단 (Thought)**: {thought}\n")
        self._append("\n".join(lines))

    def log_backtracking(
        self,
        reason: str,
        rollback_turn: int,
        taboo_list: Optional[list] = None,
    ):
        """Record backtracking rollback event and taboo list lessons learned."""
        lines = [
            f"### ⚠️ [Backtracking / Rollback Triggered]",
            f"- **Failure Reason**: `{reason}`",
            f"- **Restored Checkpoint**: Turn {rollback_turn}",
        ]
        if taboo_list:
            lines.append("- **Taboo Lessons (금지 규칙)**:")
            for item in taboo_list:
                lines.append(f"  - 🚫 {item}")
        lines.append("")
        self._append("\n".join(lines))

    def log_llm_exchange(self, prompt: str, raw_response: str):
        """Record 100% full raw prompt and LLM raw output."""
        fence_p = "````"
        while fence_p in prompt:
            fence_p += "`"
        fence_r = "````"
        while fence_r in raw_response:
            fence_r += "`"

        block = (
            f"### 📤 [LLM Input Prompt (Raw)]\n"
            f"{fence_p}text\n"
            f"{prompt}\n"
            f"{fence_p}\n\n"
            f"### 📥 [LLM Output Response (Raw)]\n"
            f"{fence_r}json\n"
            f"{raw_response}\n"
            f"{fence_r}\n"
        )
        self._append(block)

    def log_tool_execution(self, tool_name: str, args: Dict[str, Any], result: Any, duration_sec: float):
        """Record tool invocation arguments and full raw observation."""
        args_json = json.dumps(args, ensure_ascii=False, indent=2)
        result_str = str(result)
        
        # Determine fence length to prevent nested markdown/mermaid breakout
        fence = "````"
        while fence in result_str:
            fence += "`"
        
        block = (
            f"### 🛠️ [Tool Execution: `{tool_name}`]\n"
            f"- **Execution Time**: `{duration_sec:.3f}s`\n"
            f"- **Arguments (Raw)**:\n"
            f"```json\n"
            f"{args_json}\n"
            f"```\n"
            f"- **Observation Result (Raw Full Content)**:\n"
            f"{fence}text\n"
            f"{result_str}\n"
            f"{fence}\n"
        )
        self._append(block)

    def log_completion(self, final_answer: str):
        """Record final completion, duration, and answer."""
        total_duration = time.time() - self.start_time
        block = (
            f"\n---\n"
            f"## 🏁 [Task Final Completion]\n"
            f"- **Total Duration**: `{total_duration:.2f}s`\n"
            f"- **Completion Time**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
            f"- **Final Report**:\n\n"
            f"{final_answer}\n"
        )
        self._append(block)
