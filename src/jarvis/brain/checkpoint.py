"""Checkpoint Snapshot & Context Pruning Backtracking Engine for JARVIS."""

import json
import os
from pathlib import Path
import time
from typing import Any, Dict, List, Optional, Tuple
from pydantic import BaseModel, Field

from jarvis.brain.memory import ArtifactSnapshot, WorkingMemory
from jarvis.utils.logger import get_logger

logger = get_logger("brain.checkpoint")


class Checkpoint(BaseModel):
    """Snapshot data model representing a safe milestone checkpoint."""

    checkpoint_id: str = Field(description="고유 ID (예: cp_0_init, cp_1_m1_done)")
    parent_id: Optional[str] = Field(default=None, description="직전 부모 체크포인트 ID")
    turn: int = Field(default=0, description="스냅샷이 생성된 턴 수")
    phase: str = Field(default="INIT", description="당시 마일스톤 단계명")
    description: str = Field(default="", description="체크포인트 생성 사유/설명")
    timestamp: float = Field(default_factory=time.time)

    # 1. 칠판 상태 딥카피 스냅샷
    memory_snapshot: Dict[str, Any] = Field(description="WorkingMemory의 완전한 딕셔너리 덤프")

    # 2. 대화 히스토리 절단 기준점 (Context Pruning Point)
    message_index: int = Field(description="해당 시점의 messages 리스트 길이")

    # 3. 파일시스템 커밋 산출물 상태
    committed_artifacts: List[ArtifactSnapshot] = Field(default_factory=list, description="커밋된 파일 목록 및 해시")


class CheckpointManager:
    """Manages creation, history, persistence, and rollback of checkpoints."""

    def __init__(self, session_id: str, storage_dir: Optional[str] = None):
        self.session_id = session_id
        self.storage_dir = Path(storage_dir) if storage_dir else Path(".jarvis") / "sessions" / session_id / "checkpoints"
        self.history: List[Checkpoint] = []
        self.accumulated_taboo: List[str] = []

        # Ensure directory exists if path provided
        try:
            os.makedirs(self.storage_dir, exist_ok=True)
        except Exception as e:
            logger.debug(f"Could not create storage_dir '{self.storage_dir}': {e}")

    def save_checkpoint(
        self,
        memory: WorkingMemory,
        message_index: int,
        phase: str = "INIT",
        description: str = "",
        committed_artifacts: Optional[List[ArtifactSnapshot]] = None,
        turn: int = 0,
    ) -> Checkpoint:
        """Create a deep snapshot of the verified safe state."""
        parent_id = self.history[-1].checkpoint_id if self.history else None
        cp_id = f"cp_{len(self.history)}_{phase.lower()}_{int(time.time())}"

        # Deep dump of WorkingMemory
        memory_dump = memory.model_dump()

        cp = Checkpoint(
            checkpoint_id=cp_id,
            parent_id=parent_id,
            turn=turn,
            phase=phase,
            description=description,
            timestamp=time.time(),
            memory_snapshot=memory_dump,
            message_index=message_index,
            committed_artifacts=committed_artifacts or [],
        )

        self.history.append(cp)
        logger.info(f"Saved Checkpoint '{cp_id}' at turn {turn}, phase '{phase}', msg_idx: {message_index}")

        # Optional persistence to disk
        try:
            file_path = self.storage_dir / f"{cp_id}.json"
            file_path.write_text(cp.model_dump_json(indent=2), encoding="utf-8")
        except Exception as e:
            logger.debug(f"Failed to persist checkpoint to disk: {e}")

        return cp

    def get_latest_safe_checkpoint(self) -> Optional[Checkpoint]:
        """Return the most recently saved safe checkpoint."""
        return self.history[-1] if self.history else None

    def rollback_to(
        self,
        checkpoint_id: Optional[str] = None,
        failure_reason: Optional[str] = None,
    ) -> Tuple[WorkingMemory, int]:
        """Rollback to target checkpoint, prune messages index, and inject taboo lesson."""
        if not self.history:
            raise RuntimeError("Cannot rollback: No checkpoints saved in history.")

        # Find checkpoint
        target_cp: Optional[Checkpoint] = None
        if checkpoint_id:
            for cp in reversed(self.history):
                if cp.checkpoint_id == checkpoint_id:
                    target_cp = cp
                    break
        if target_cp is None:
            target_cp = self.history[-1]

        # Restore WorkingMemory
        restored_memory = WorkingMemory.model_validate(target_cp.memory_snapshot)

        # Inject failure lesson into taboo list
        if failure_reason:
            clean_reason = failure_reason.strip()
            if clean_reason not in self.accumulated_taboo:
                self.accumulated_taboo.append(clean_reason)

        for lesson in self.accumulated_taboo:
            if lesson not in restored_memory.taboo_list:
                restored_memory.taboo_list.append(lesson)

        logger.info(
            f"Rolled back to checkpoint '{target_cp.checkpoint_id}'. "
            f"Context prune index: {target_cp.message_index}. "
            f"Taboo count: {len(restored_memory.taboo_list)}"
        )

        return restored_memory, target_cp.message_index

    def get_checkpoint_count(self) -> int:
        """Return total number of saved checkpoints."""
        return len(self.history)
