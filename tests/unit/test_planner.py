"""Unit tests for JARVIS Task Planner (TDD Red-Green)."""

import pytest
from jarvis.brain.planner import TaskPlanner, TaskPlan, PlanStep, EngineOption


def test_task_planner_create_plan_vision_excel():
    """TaskPlanner should decompose image-to-excel instruction into structured steps with options."""
    planner = TaskPlanner()
    instruction = "화면 영수증 캡처해서 엑셀 파일로 정리해줘"

    plan = planner.create_plan(instruction)

    assert isinstance(plan, TaskPlan)
    assert len(plan.steps) == 2

    # Step 1: Vision analysis
    step1 = plan.steps[0]
    assert "분석" in step1.title or "추출" in step1.title
    assert len(step1.options) >= 2
    assert step1.options[0].recommended is True
    assert "Gemini" in step1.options[0].name

    # Step 2: Excel creation
    step2 = plan.steps[1]
    assert "엑셀" in step2.title or "스프레드시트" in step2.title
    assert len(step2.options) >= 1
    assert "openpyxl" in step2.options[0].name or "Python" in step2.options[0].name


def test_task_planner_create_plan_form_filling():
    """TaskPlanner should detect form filling tasks."""
    planner = TaskPlanner()
    instruction = "이 명단 데이터 웹 양식에 순차적으로 입력해줘"

    plan = planner.create_plan(instruction)

    assert isinstance(plan, TaskPlan)
    assert len(plan.steps) >= 1


def test_task_planner_detects_directory_scan():
    """TaskPlanner should detect local directory scan intent."""
    planner = TaskPlanner()
    instruction = r"C:\Users\majun\Coding\javis 폴더구조 엑셀로 정리해줘"

    plan = planner.create_plan(instruction)
    assert plan.intent == "DIRECTORY_SCAN"
    assert "scan_directory" in [a.tool_name for a in plan.actions]
    assert "create_excel" in [a.tool_name for a in plan.actions]


def test_task_planner_detects_batch_receipts():
    """TaskPlanner should detect batch receipt document analysis intent."""
    planner = TaskPlanner()
    instruction = r"C:\Receipts 폴더에 있는 영수증들 전부 보고 엑셀로 만들어줘"

    plan = planner.create_plan(instruction)
    assert plan.intent == "BATCH_DOCUMENT_ANALYSIS"
    assert "batch_analyze_documents" in [a.tool_name for a in plan.actions]
    assert "create_excel" in [a.tool_name for a in plan.actions]

