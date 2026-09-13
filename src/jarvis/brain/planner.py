"""Autonomous Task Planner detecting user intent, paths, and selecting optimal Tool sets."""

import re
from pathlib import Path
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from jarvis.utils.logger import get_logger

logger = get_logger("brain.planner")


class PlannedAction(BaseModel):
    """An atomic tool invocation planned by AI Brain."""
    tool_name: str
    args: Dict[str, Any] = Field(default_factory=dict)
    tier: int = 1  # 1: Green (Auto), 2: Yellow (Approval), 3: Red (Blocked/Warning)
    description: str = ""


class EngineOption(BaseModel):
    """User selectable engine option for a task step."""
    id: int
    name: str
    description: str
    recommended: bool = False
    engine_type: str = "gemini"


class PlanStep(BaseModel):
    """User-facing execution plan step."""
    step_num: int
    title: str
    description: str = ""
    options: List[EngineOption] = Field(default_factory=list)
    selected_option_id: int = 1

    @property
    def selected_option(self) -> Optional[EngineOption]:
        for opt in self.options:
            if opt.id == self.selected_option_id:
                return opt
        return self.options[0] if self.options else None


class TaskPlan(BaseModel):
    """Decomposed plan containing tool actions and interactive UI steps."""
    instruction: str
    intent: str  # "DIRECTORY_SCAN", "BATCH_DOCUMENT_ANALYSIS", "SCREEN_VISION", "FORM_FILLING"
    target_path: Optional[str] = None
    actions: List[PlannedAction] = Field(default_factory=list)
    steps: List[PlanStep] = Field(default_factory=list)


class TaskPlanner:
    """Analyzes user instruction, extracts paths/intents, and generates autonomous tool plans."""

    def _extract_path(self, text: str) -> Optional[Path]:
        """Extract Windows file/folder path from natural language instruction."""
        # Match Windows full path (e.g. C:\Users\..., C:/Users/..., or \path\...)
        path_pattern = r'([a-zA-Z]:[\\/][^\s가-힣\*\?\"\<\>\|]+)'
        match = re.search(path_pattern, text)
        if match:
            raw_path = match.group(1).rstrip(",. ")
            try:
                candidate = Path(raw_path)
                if candidate.exists():
                    return candidate
                # Try stripping trailing non-path words
                return candidate
            except Exception:
                pass
        return None

    def create_plan(self, instruction: str) -> TaskPlan:
        """Decompose user instruction into intent, target path, and planned tool actions."""
        logger.info(f"Analyzing instruction: '{instruction}'")
        text = instruction.strip()
        text_lower = text.lower()

        extracted_path = self._extract_path(text)
        path_str = str(extracted_path) if extracted_path else None

        is_receipt_task = any(kw in text_lower for kw in ("영수증", "명세서", "지출", "비용", "receipt"))
        is_structure_task = any(kw in text_lower for kw in ("폴더구조", "폴더 구조", "디렉터리", "파일목록", "파일트리", "tree"))
        is_screen_capture = any(kw in text_lower for kw in ("화면", "캡처", "현재화면", "screen", "screenshot"))

        # -------------------------------------------------------------
        # 1. Intent: BATCH_DOCUMENT_ANALYSIS (Scenario B)
        # -------------------------------------------------------------
        if (extracted_path or "폴더" in text_lower) and is_receipt_task and not is_screen_capture:
            target_dir = path_str or str(Path.cwd())
            plan = TaskPlan(
                instruction=instruction,
                intent="BATCH_DOCUMENT_ANALYSIS",
                target_path=target_dir,
                actions=[
                    PlannedAction(
                        tool_name="scan_directory",
                        args={"path": target_dir, "recursive": True},
                        tier=1,
                        description=f"'{target_dir}' 폴더 내 영수증/문서 파일 목록 탐색",
                    ),
                    PlannedAction(
                        tool_name="batch_analyze_documents",
                        args={"provider": "gemini"},
                        tier=1,
                        description="발견된 영수증들을 Gemini 비전으로 일괄 정형 데이터 추출",
                    ),
                    PlannedAction(
                        tool_name="create_excel",
                        args={"sheet_name": "영수증정산"},
                        tier=1,
                        description="추출된 영수증 데이터를 취합하여 스타일 엑셀 생성",
                    ),
                ],
                steps=[
                    PlanStep(
                        step_num=1,
                        title=f"폴더 내 영수증 일괄 비전 분석 ({Path(target_dir).name})",
                        description="폴더의 모든 이미지/PDF 영수증을 순회하며 데이터 일괄 추출",
                        options=[
                            EngineOption(id=1, name="Google Gemini 3.6 Flash [권장]", description="고속 비전 정밀 추출", recommended=True, engine_type="gemini"),
                            EngineOption(id=2, name="로컬 Ollama Qwen2.5 14B", description="오프라인 텍스트 처리", recommended=False, engine_type="ollama"),
                        ]
                    ),
                    PlanStep(
                        step_num=2,
                        title="종합 정산 엑셀 스프레드시트 생성",
                        description="모든 영수증 데이터를 통합하고 합계 금액이 적용된 .xlsx 생성",
                        options=[
                            EngineOption(id=1, name="Python openpyxl 엔진 [권장]", description="스타일링 완비 엑셀 생성", recommended=True, engine_type="python"),
                        ]
                    )
                ]
            )
            return plan

        # -------------------------------------------------------------
        # 2. Intent: DIRECTORY_SCAN (Scenario A)
        # -------------------------------------------------------------
        elif extracted_path or is_structure_task:
            target_dir = path_str or str(Path.cwd())
            plan = TaskPlan(
                instruction=instruction,
                intent="DIRECTORY_SCAN",
                target_path=target_dir,
                actions=[
                    PlannedAction(
                        tool_name="scan_directory",
                        args={"path": target_dir, "recursive": True},
                        tier=1,
                        description=f"'{target_dir}' 디렉터리 파일/폴더 구조 스캔",
                    ),
                    PlannedAction(
                        tool_name="create_excel",
                        args={"sheet_name": "폴더구조"},
                        tier=1,
                        description="스캔된 폴더 트리를 계층형 스타일 엑셀로 생성",
                    ),
                ],
                steps=[
                    PlanStep(
                        step_num=1,
                        title=f"로컬 파일시스템 구조 스캔 ({Path(target_dir).name})",
                        description="실제 디렉터리를 탐색하여 파일 트리, 크기, 수정일 메타데이터 수집",
                        options=[
                            EngineOption(id=1, name="OS Filesystem Scanner [권장]", description="0.1초 고속 무손실 파일 트리 스캔", recommended=True, engine_type="python"),
                        ]
                    ),
                    PlanStep(
                        step_num=2,
                        title="폴더 구조 엑셀 스프레드시트 생성",
                        description="파일 목록과 크기, 수정일자가 포함된 스타일 엑셀 생성",
                        options=[
                            EngineOption(id=1, name="Python openpyxl 엔진 [권장]", description="비즈니스 서식 적용 엑셀 생성", recommended=True, engine_type="python"),
                        ]
                    )
                ]
            )
            return plan

        # -------------------------------------------------------------
        # 3. Default Intent: SCREEN_VISION
        # -------------------------------------------------------------
        else:
            plan = TaskPlan(
                instruction=instruction,
                intent="SCREEN_VISION",
                actions=[
                    PlannedAction(
                        tool_name="capture_screen",
                        args={},
                        tier=1,
                        description="현재 활성 화면 캡처",
                    ),
                    PlannedAction(
                        tool_name="analyze_document",
                        args={"provider": "gemini"},
                        tier=1,
                        description="화면 이미지에서 정형 데이터 추출",
                    ),
                    PlannedAction(
                        tool_name="create_excel",
                        args={"sheet_name": "작업결과"},
                        tier=1,
                        description="추출된 데이터로 엑셀 생성",
                    ),
                ],
                steps=[
                    PlanStep(
                        step_num=1,
                        title="화면 캡처 및 시각 데이터 분석",
                        description="화면 속 문서/표를 Gemini 비전으로 정형 추출",
                        options=[
                            EngineOption(id=1, name="Google Gemini 3.6 Flash [권장]", description="클라우드 고속 비전 분석", recommended=True, engine_type="gemini"),
                            EngineOption(id=2, name="로컬 Ollama Qwen2.5 14B", description="오프라인 처리", recommended=False, engine_type="ollama"),
                        ]
                    ),
                    PlanStep(
                        step_num=2,
                        title="스마트 엑셀 스프레드시트 생성",
                        description="추출된 데이터를 바탕으로 스타일링 .xlsx 생성",
                        options=[
                            EngineOption(id=1, name="Python openpyxl 엔진 [권장]", description="서식 적용 엑셀 생성", recommended=True, engine_type="python"),
                        ]
                    )
                ]
            )
            return plan
