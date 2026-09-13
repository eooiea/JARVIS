"""Unit tests for Checkpoint Snapshot and Context Pruning Backtracking Engine (TDD)."""

import os
import shutil
import tempfile
from pathlib import Path
import pytest

from jarvis.brain.memory import WorkingMemory, Milestone, ArtifactSnapshot
from jarvis.brain.checkpoint import Checkpoint, CheckpointManager


class TestCheckpointEngine:
    """Test suite for safe checkpointing, context pruning indices, and taboo injection."""

    @pytest.fixture
    def session_dir(self):
        temp_dir = tempfile.mkdtemp(prefix="jarvis_cp_test_")
        yield temp_dir
        shutil.rmtree(temp_dir, ignore_errors=True)

    def test_checkpoint_model_creation(self):
        snap = Checkpoint(
            checkpoint_id="cp_0_init",
            turn=1,
            phase="INIT",
            description="초기 마일스톤 수립",
            memory_snapshot={"main_goal": "목표", "milestones": []},
            message_index=2,
            committed_artifacts=[],
        )
        assert snap.checkpoint_id == "cp_0_init"
        assert snap.turn == 1
        assert snap.message_index == 2
        assert snap.memory_snapshot["main_goal"] == "목표"

    def test_save_and_retrieve_checkpoint(self, session_dir):
        mgr = CheckpointManager(session_id="test_sess_01", storage_dir=session_dir)
        wm = WorkingMemory(
            main_goal="정리 작업",
            current_phase="INIT",
            milestones=[Milestone(id=1, title="1단계", status="DONE")],
        )

        cp = mgr.save_checkpoint(
            memory=wm,
            message_index=3,
            phase="INIT",
            description="1단계 완료 후 체크포인트",
            turn=1,
        )

        assert cp.checkpoint_id.startswith("cp_")
        assert mgr.get_checkpoint_count() == 1
        latest = mgr.get_latest_safe_checkpoint()
        assert latest is not None
        assert latest.checkpoint_id == cp.checkpoint_id
        assert latest.message_index == 3

    def test_rollback_restores_memory_and_message_index(self, session_dir):
        mgr = CheckpointManager(session_id="test_sess_02", storage_dir=session_dir)
        initial_wm = WorkingMemory(
            main_goal="정리 작업",
            current_phase="INIT",
            milestones=[Milestone(id=1, title="1단계", status="TODO")],
            key_findings={"key1": "safe_val"},
            taboo_list=[],
        )

        # 1. Save checkpoint at safe turn 1 with message_index 2
        mgr.save_checkpoint(
            memory=initial_wm,
            message_index=2,
            phase="INIT",
            description="안전 시점",
            turn=1,
        )

        # 2. Simulate subsequent dirty state in turn 2
        dirty_wm = WorkingMemory(
            main_goal="정리 작업",
            current_phase="BROKEN_PHASE",
            milestones=[Milestone(id=1, title="1단계", status="FAILED")],
            key_findings={"key1": "corrupted_val"},
            taboo_list=[],
        )

        # 3. Rollback to safe checkpoint with failure reason
        restored_wm, prune_idx = mgr.rollback_to(
            failure_reason="CSV 인코딩 오류로 01.csv 파싱 실패"
        )

        # Verify message_index for context pruning
        assert prune_idx == 2

        # Verify WorkingMemory state restored to safe checkpoint
        assert restored_wm.current_phase == "INIT"
        assert restored_wm.milestones[0].status == "TODO"
        assert restored_wm.key_findings["key1"] == "safe_val"

        # Verify Taboo lesson injected
        assert len(restored_wm.taboo_list) == 1
        assert "CSV 인코딩 오류" in restored_wm.taboo_list[0]

    def test_rollback_preserves_accumulated_taboo_and_findings(self, session_dir):
        """Ensure repeated rollbacks accumulate taboo list lessons."""
        mgr = CheckpointManager(session_id="test_sess_03", storage_dir=session_dir)
        wm = WorkingMemory(main_goal="목표")
        mgr.save_checkpoint(memory=wm, message_index=1, phase="INIT", description="init", turn=0)

        # 1st rollback
        wm1, _ = mgr.rollback_to(failure_reason="시도 1 실패: 접근 거부")
        assert len(wm1.taboo_list) == 1

        # 2nd rollback
        wm2, _ = mgr.rollback_to(failure_reason="시도 2 실패: 포맷 에러")
        assert len(wm2.taboo_list) == 2
        assert "접근 거부" in wm2.taboo_list[0]
        assert "포맷 에러" in wm2.taboo_list[1]
