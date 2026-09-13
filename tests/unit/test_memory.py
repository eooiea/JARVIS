"""Unit tests for JARVIS Working Memory, BlackboardOutputParser, and PromptBuilder (TDD)."""

import pytest
from jarvis.brain.memory import (
    Milestone,
    ArtifactSnapshot,
    WorkingMemory,
    BlackboardOutputParser,
    apply_blackboard_delta,
    render_blackboard,
    PromptBuilder,
)


class TestWorkingMemorySchema:
    """Test suite for WorkingMemory and related Pydantic data models."""

    def test_milestone_creation_and_defaults(self):
        m = Milestone(id=1, title="파일 목록 스캔")
        assert m.id == 1
        assert m.title == "파일 목록 스캔"
        assert m.status == "TODO"

    def test_artifact_snapshot_creation(self):
        snap = ArtifactSnapshot(path="outputs/summary.xlsx", sha256="abc123hash", size_bytes=1024)
        assert snap.path == "outputs/summary.xlsx"
        assert snap.sha256 == "abc123hash"
        assert snap.size_bytes == 1024

    def test_working_memory_defaults_and_serialization(self):
        wm = WorkingMemory(main_goal="영수증 정리해서 엑셀 생성")
        assert wm.main_goal == "영수증 정리해서 엑셀 생성"
        assert wm.current_phase == "INIT"
        assert wm.milestones == []
        assert wm.key_findings == {}
        assert wm.taboo_list == []
        assert wm.retry_count == 0

        # Serialization & Deserialization (deepcopy safety)
        dump = wm.model_dump()
        restored = WorkingMemory.model_validate(dump)
        assert restored == wm


class TestBlackboardOutputParser:
    """Test suite for 3-tier resilient XML/YAML blackboard parser."""

    def test_parse_normal_tags(self):
        raw_text = (
            "<thought>\n"
            "파일 스캔을 마쳤으므로 다음은 엑셀 생성입니다.\n"
            "</thought>\n"
            "<blackboard>\n"
            "phase: EXCEL_EXPORT\n"
            "update_milestones:\n"
            "  - id: 1\n"
            "    status: DONE\n"
            "add_findings:\n"
            "  file_count: 10\n"
            "status: CONTINUE\n"
            "</blackboard>\n"
            "엑셀 생성을 준비하고 있습니다."
        )
        parsed = BlackboardOutputParser.parse(raw_text)
        assert parsed["thought"] == "파일 스캔을 마쳤으므로 다음은 엑셀 생성입니다."
        assert parsed["blackboard_delta"]["phase"] == "EXCEL_EXPORT"
        assert parsed["blackboard_delta"]["update_milestones"] == [{"id": 1, "status": "DONE"}]
        assert parsed["blackboard_delta"]["add_findings"] == {"file_count": 10}
        assert parsed["blackboard_delta"]["status"] == "CONTINUE"
        assert parsed["clean_text"] == "엑셀 생성을 준비하고 있습니다."

    def test_parse_missing_closing_tags(self):
        """Simulate local 7B model omitting </thought> or </blackboard>."""
        raw_text = (
            "<thought>\n"
            "태그 닫기를 깜빡함\n"
            "<blackboard>\n"
            "phase: SCAN\n"
            "status: CONTINUE\n"
        )
        parsed = BlackboardOutputParser.parse(raw_text)
        assert "태그 닫기를 깜빡함" in parsed["thought"]
        assert parsed["blackboard_delta"].get("phase") == "SCAN"
        assert parsed["blackboard_delta"].get("status") == "CONTINUE"

    def test_parse_malformed_yaml_fallback(self):
        """Simulate YAML syntax indentation error falling back to line-by-line regex parsing."""
        raw_text = (
            "<thought>테스트</thought>\n"
            "<blackboard>\n"
            "phase: PARSE_ERROR_TEST\n"
            "  invalid_tab_indent: 123\n"
            "status: DEAD_END\n"
            "dead_end_reason: 인코딩 복구 불가\n"
            "</blackboard>"
        )
        parsed = BlackboardOutputParser.parse(raw_text)
        assert parsed["blackboard_delta"]["phase"] == "PARSE_ERROR_TEST"
        assert parsed["blackboard_delta"]["status"] == "DEAD_END"
        assert parsed["blackboard_delta"]["dead_end_reason"] == "인코딩 복구 불가"

    def test_parse_empty_or_no_tags(self):
        raw_text = "안녕하세요! 무엇을 도와드릴까요?"
        parsed = BlackboardOutputParser.parse(raw_text)
        assert parsed["thought"] == ""
        assert parsed["blackboard_delta"] == {}
        assert parsed["clean_text"] == "안녕하세요! 무엇을 도와드릴까요?"


class TestBlackboardDeltaApplication:
    """Test applying parsed delta to WorkingMemory object."""

    def test_apply_phase_update(self):
        wm = WorkingMemory(main_goal="목표")
        delta = {"phase": "EXECUTION"}
        apply_blackboard_delta(wm, delta)
        assert wm.current_phase == "EXECUTION"

    def test_apply_milestones_update(self):
        wm = WorkingMemory(
            main_goal="목표",
            milestones=[
                Milestone(id=1, title="1단계", status="TODO"),
                Milestone(id=2, title="2단계", status="TODO"),
            ],
        )
        delta = {
            "update_milestones": [
                {"id": 1, "status": "DONE"},
                {"id": 2, "status": "IN_PROGRESS"},
            ]
        }
        apply_blackboard_delta(wm, delta)
        assert wm.milestones[0].status == "DONE"
        assert wm.milestones[1].status == "IN_PROGRESS"

    def test_apply_findings_upsert(self):
        wm = WorkingMemory(
            main_goal="목표",
            key_findings={"existing_key": "val1", "overwrite_key": "old"},
        )
        delta = {
            "add_findings": {
                "overwrite_key": "new",
                "new_key": 42,
            }
        }
        apply_blackboard_delta(wm, delta)
        assert wm.key_findings["existing_key"] == "val1"
        assert wm.key_findings["overwrite_key"] == "new"
        assert wm.key_findings["new_key"] == 42


class TestPromptBuilderAndRenderer:
    """Test KV-cache layout separation: Immutable Prefix vs Dynamic Working Blackboard."""

    def test_render_blackboard_text(self):
        wm = WorkingMemory(
            main_goal="영수증 정리",
            current_phase="SCAN",
            milestones=[
                Milestone(id=1, title="파일 목록 스캔", status="IN_PROGRESS"),
                Milestone(id=2, title="엑셀 취합", status="TODO"),
            ],
            key_findings={"scanned_count": 5},
            taboo_list=["손상된 01.jpg 직접 파싱 금지"],
        )
        bb_text = render_blackboard(wm)
        assert "[JARVIS CURRENT WORKING BLACKBOARD]" in bb_text
        assert "Phase: SCAN" in bb_text
        assert "[1] 파일 목록 스캔: IN_PROGRESS" in bb_text
        assert "[2] 엑셀 취합: TODO" in bb_text
        assert "scanned_count: 5" in bb_text
        assert "손상된 01.jpg 직접 파싱 금지" in bb_text

    def test_prompt_builder_structure(self):
        wm = WorkingMemory(main_goal="최종 목표")
        builder = PromptBuilder(system_instruction="고정 지침", tool_schemas=[{"name": "test_tool"}])
        
        # 1. Immutable Prefix
        prefix = builder.build_immutable_prefix(wm.main_goal)
        assert "고정 지침" in prefix
        assert "test_tool" in prefix
        assert "최종 목표" in prefix

        # 2. Dynamic Turns
        full_prompt = builder.build_full_prompt(wm, recent_messages=[{"role": "user", "content": "hello"}])
        assert prefix in full_prompt
        assert "[JARVIS CURRENT WORKING BLACKBOARD]" in full_prompt
        assert "hello" in full_prompt
