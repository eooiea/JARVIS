"""Working Memory, Blackboard Parser, and KV-Cache Safe Prompt Builder for JARVIS."""

import json
import re
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field
import yaml


class Milestone(BaseModel):
    """Hierarchical milestone step."""
    id: int
    title: str
    status: str = "TODO"  # "TODO" | "IN_PROGRESS" | "DONE" | "FAILED"


class ArtifactSnapshot(BaseModel):
    """Snapshot of a committed file for integrity verification."""
    path: str
    sha256: str
    size_bytes: int


class WorkingMemory(BaseModel):
    """Agent's Working Memory / Blackboard state."""
    main_goal: str = Field(description="사용자가 요청한 최종 목표 및 산출물 형태")
    current_phase: str = Field(default="INIT", description="현재 활성화된 작업 단계")
    milestones: List[Milestone] = Field(default_factory=list, description="계층형 고수준 마일스톤")
    key_findings: Dict[str, Any] = Field(default_factory=dict, description="중간 발견 데이터/변수/경로")
    taboo_list: List[str] = Field(default_factory=list, description="실패한 경로 및 핵심 실패 교훈")
    retry_count: int = Field(default=0, description="현재 분기점에서의 재시도 횟수")


class BlackboardOutputParser:
    """3-tier resilient parser extracting thought, blackboard delta, and clean user text from LLM response."""

    THOUGHT_PATTERN = re.compile(r"<thought>(.*?)(?:</thought>|$)", re.DOTALL | re.IGNORECASE)
    BLACKBOARD_PATTERN = re.compile(r"<blackboard>(.*?)(?:</blackboard>|$)", re.DOTALL | re.IGNORECASE)

    @classmethod
    def parse(cls, raw_text: str) -> Dict[str, Any]:
        """Parse raw LLM string into thought, blackboard_delta dict, and clean user text."""
        if not raw_text:
            return {"thought": "", "blackboard_delta": {}, "clean_text": ""}

        # 1. Thought extraction
        thought_match = cls.THOUGHT_PATTERN.search(raw_text)
        thought = ""
        if thought_match:
            raw_thought = thought_match.group(1).strip()
            # If the closing tag was missing and blackboard tag starts inside, cut before blackboard
            bb_index = re.search(r"<blackboard>", raw_thought, re.IGNORECASE)
            if bb_index:
                thought = raw_thought[:bb_index.start()].strip()
            else:
                thought = raw_thought

        # 2. Blackboard extraction & parsing
        blackboard_delta: Dict[str, Any] = {}
        bb_match = cls.BLACKBOARD_PATTERN.search(raw_text)
        if bb_match:
            bb_raw = bb_match.group(1).strip()
            try:
                parsed = yaml.safe_load(bb_raw)
                if isinstance(parsed, dict):
                    blackboard_delta = parsed
            except Exception:
                # Fallback: regex key-value extraction
                for line in bb_raw.splitlines():
                    clean_line = line.strip()
                    if ":" in clean_line and not clean_line.startswith("-"):
                        k, v = clean_line.split(":", 1)
                        blackboard_delta[k.strip()] = v.strip().strip("\"'")

        # 3. Clean user-facing text
        clean_text = cls.BLACKBOARD_PATTERN.sub("", cls.THOUGHT_PATTERN.sub("", raw_text)).strip()

        return {
            "thought": thought,
            "blackboard_delta": blackboard_delta,
            "clean_text": clean_text,
        }


def apply_blackboard_delta(memory: WorkingMemory, delta: Dict[str, Any]) -> None:
    """Apply delta updates from LLM blackboard tag to WorkingMemory."""
    if not delta:
        return

    # 1. Phase update
    if "phase" in delta and delta["phase"]:
        memory.current_phase = str(delta["phase"]).strip()

    # 2. Milestones update
    if "update_milestones" in delta and isinstance(delta["update_milestones"], list):
        for item in delta["update_milestones"]:
            if isinstance(item, dict) and "id" in item and "status" in item:
                target_id = item["id"]
                new_status = item["status"]
                for m in memory.milestones:
                    if m.id == target_id:
                        m.status = str(new_status).strip()

    # 3. Key findings upsert
    if "add_findings" in delta and isinstance(delta["add_findings"], dict):
        memory.key_findings.update(delta["add_findings"])


def render_blackboard(memory: WorkingMemory) -> str:
    """Render WorkingMemory state as formatted string for LLM injection."""
    lines = [
        "📋 [JARVIS CURRENT WORKING BLACKBOARD]",
        f"- Phase: {memory.current_phase}",
        "- Milestones:",
    ]
    if memory.milestones:
        for m in memory.milestones:
            lines.append(f"  [{m.id}] {m.title}: {m.status}")
    else:
        lines.append("  (No milestones defined)")

    lines.append("- Key Findings:")
    if memory.key_findings:
        for k, v in memory.key_findings.items():
            lines.append(f"  {k}: {v}")
    else:
        lines.append("  (None)")

    lines.append("- [🚨 절대 금지 규칙 - Taboo List (절대 재시도 금지)]:")
    if memory.taboo_list:
        for t in memory.taboo_list:
            lines.append(f"  - 🚫 {t} (※ 이미 실패가 확정되었으므로 절대 다시 호출하지 말고 대안을 실행하십시오.)")
    else:
        lines.append("  (None)")

    return "\n".join(lines)


class PromptBuilder:
    """Builds KV-cache safe prompts separating immutable prefix from dynamic working state."""

    def __init__(
        self,
        system_instruction: str,
        tool_schemas: Optional[List[Dict[str, Any]]] = None,
    ):
        self.system_instruction = system_instruction
        self.tool_schemas = tool_schemas or []

    def build_immutable_prefix(self, main_goal: str) -> str:
        """Construct immutable prefix block (100% KV-Cache Hit across turns)."""
        tools_str = json.dumps(self.tool_schemas, ensure_ascii=False, indent=2)
        return (
            f"{self.system_instruction}\n\n"
            f"[도구 명세 스키마]\n{tools_str}\n\n"
            f"[사용자 최종 목표]\n{main_goal}"
        )

    def build_full_prompt(
        self,
        memory: WorkingMemory,
        recent_messages: Optional[List[Dict[str, Any]]] = None,
    ) -> str:
        """Assemble full prompt: Immutable Prefix + Dynamic Blackboard + Recent turns."""
        prefix = self.build_immutable_prefix(memory.main_goal)
        blackboard = render_blackboard(memory)

        msg_lines = []
        if recent_messages:
            msg_lines.append("[최근 대화 및 실행 내역]")
            for msg in recent_messages:
                role = msg.get("role", "user")
                content = msg.get("content", "")
                msg_lines.append(f"[{role}]: {content}")

        messages_block = "\n".join(msg_lines) if msg_lines else ""

        blocks = [prefix, blackboard]
        if messages_block:
            blocks.append(messages_block)

        return "\n\n".join(blocks)
