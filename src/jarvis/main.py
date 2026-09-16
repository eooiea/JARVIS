"""JARVIS Autonomous Agent Main Entrypoint & True Tool-Calling Orchestrator."""

import sys
from pathlib import Path
from typing import Optional, Dict, Any

from jarvis.utils.config import JarvisConfig, load_config
from jarvis.utils.logger import setup_logger, get_logger
from jarvis.cli.app import JarvisCLI
from jarvis.tools.registry import ToolRegistry
from jarvis.tools.filesystem import scan_directory, read_file, write_file
from jarvis.tools.vision import analyze_document, batch_analyze_documents, capture_screen
from jarvis.tools.office import create_excel, inspect_excel, get_courier_preset, transform_excel, batch_transform_orders
from jarvis.brain.agent import JarvisAgent
from jarvis.utils.session_logger import SessionLogger
from jarvis.guardrails.killswitch import KillSwitch, EmergencyStopException
from jarvis.guardrails.permissions import PermissionManager
from jarvis.providers.base import BaseLLMProvider
from jarvis.providers.factory import get_llm_provider

logger = get_logger("main")


class JarvisPipeline:
    """True Autonomous Agent Pipeline: LLM Brain drives dynamic Tool Calling loops."""

    def __init__(
        self,
        config: Optional[JarvisConfig] = None,
        provider: Optional[BaseLLMProvider] = None,
        screen_capture: Optional[Any] = None,
        output_dir: Optional[Path | str] = None,
        log_dir: Optional[Path | str] = None,
    ):
        self.config = config or load_config()
        self.cli = JarvisCLI(config=self.config)
        self.killswitch = KillSwitch()
        
        self.output_dir = Path(output_dir).resolve() if output_dir else self.config.get_output_path()
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.permissions = PermissionManager(allowed_output_dir=self.output_dir)

        self.log_dir = Path(log_dir).resolve() if log_dir else (Path.cwd() / "logs")
        self.log_dir.mkdir(parents=True, exist_ok=True)

        # Initialize LLM Brain
        self.provider = provider or get_llm_provider(config=self.config)

        # 1. Register all tools into Registry
        self.registry = ToolRegistry()
        self._register_default_tools()

        # 2. Initialize Autonomous Agent
        self.agent = JarvisAgent(
            provider=self.provider,
            tool_registry=self.registry,
            max_turns=8,
        )

    def _register_default_tools(self):
        """Register core OS tools available for the LLM Brain to invoke."""

        def safe_scan_directory(path: str, recursive: bool = True) -> Any:
            """디렉터리 내의 파일 및 서브 폴더 목록, 크기, 수정일자 메타데이터를 스캔합니다.
            
            Args:
                path: 스캔할 로컬 디렉터리 경로 (예: 'C:/Users/.../project').
                recursive: 하위 폴더까지 재귀적으로 스캔할지 여부.
            """
            self.permissions.check_permission("read_safe", target_path=path)
            return scan_directory(path, recursive=recursive)

        def safe_read_file(path: str) -> str:
            """텍스트/CSV/코드/설정 파일의 내용을 읽어옵니다.
            
            Args:
                path: 읽을 파일의 경로.
            """
            self.permissions.check_permission("read_safe", target_path=path)
            return read_file(path)

        def safe_write_file(path: str, content: str) -> str:
            """텍스트 파일에 내용을 저장합니다.
            
            Args:
                path: 저장할 파일 경로.
                content: 저장할 텍스트 내용.
            """
            self.permissions.check_permission("create_file", target_path=path)
            p = write_file(path, content)
            return str(p)

        def safe_create_excel(data: Any, output_path: Optional[str] = None, sheet_name: str = "Data") -> str:
            """정형 데이터(딕셔너리 리스트)를 스타일링된 비즈니스 엑셀(.xlsx) 파일로 생성합니다.
            
            Args:
                data: 엑셀 행으로 기록할 데이터 목록 (list of dicts).
                output_path: 저장할 파일 경로 (생략 시 outputs/ 폴더에 자동 작명 저장).
                sheet_name: 엑셀 시트 이름.
            """
            target = Path(output_path) if output_path else (self.output_dir / "작업결과.xlsx")
            self.permissions.check_permission("create_file", target_path=target)
            created = create_excel(data=data, output_path=target, sheet_name=sheet_name, auto_number=True)
            return f"엑셀 파일 생성 완료: {created}"

        def safe_analyze_document(file_path: str, prompt: Optional[str] = None) -> Any:
            """단일 이미지나 PDF 영수증/표/문서를 Gemini 비전으로 분석하여 정형 JSON을 추출합니다.
            
            Args:
                file_path: 분석할 이미지 또는 PDF 파일 경로.
                prompt: 분석 시 특별히 집중할 지시사항.
            """
            self.permissions.check_permission("read_safe", target_path=file_path)
            return analyze_document(file_path, provider=self.provider, prompt=prompt)

        def safe_batch_analyze_documents(file_paths: list, prompt: Optional[str] = None) -> Any:
            """여러 개의 이미지/PDF 영수증 목록을 순회하며 일괄 비전 추출합니다.
            
            Args:
                file_paths: 분석할 파일 경로 목록.
                prompt: 분석 시 특별히 집중할 지시사항.
            """
            return batch_analyze_documents(file_paths, provider=self.provider, prompt=prompt)

        def safe_capture_screen() -> str:
            """현재 컴퓨터 모니터 화면을 캡처합니다."""
            b = capture_screen()
            temp_path = self.output_dir / "latest_screen_capture.png"
            temp_path.write_bytes(b)
            return str(temp_path)

        def safe_inspect_excel(file_path: str, max_sample_rows: int = 1) -> Any:
            """엑셀 파일의 시트 목록, 컬럼 헤더, 샘플 데이터를 최소 토큰으로 빠르게 조회합니다.
            
            Args:
                file_path: 조회할 엑셀 파일 경로.
                max_sample_rows: 미리보기할 샘플 행 수 (기본 1).
            """
            self.permissions.check_permission("read_safe", target_path=file_path)
            return inspect_excel(file_path, max_sample_rows=max_sample_rows)

        def safe_get_courier_preset(courier_name: str) -> Any:
            """국내 5대 택배사(CJ대한통운, 우체국택배, 한진택배, 롯데택배, 로젠택배)의 표준 송장 헤더 및 필수 필드 규격을 조회합니다.
            
            Args:
                courier_name: 택배사 명칭 (예: 'CJ대한통운', '우체국', '한진', '롯데', '로젠').
            """
            return get_courier_preset(courier_name)

        def safe_transform_excel(
            source_path: str,
            mapping_rules: dict,
            target_schema: Optional[list] = None,
            required_fields: Optional[list] = None,
        ) -> Any:
            """소스 엑셀 데이터를 매핑 규칙에 따라 타깃 헤더 규격으로 초고속 정규화 및 변환합니다.
            
            Args:
                source_path: 변환할 엑셀 파일 경로.
                mapping_rules: 소스 컬럼 -> 타깃 컬럼 매핑 규칙 (예: {"받는사람": "받는분성명"}).
                target_schema: 최종 결과 컬럼 순서 리스트.
                required_fields: 필수 타깃 컬럼 목록 (생략 시 자동 감지).
            """
            self.permissions.check_permission("read_safe", target_path=source_path)
            return transform_excel(
                source_path=source_path,
                mapping_rules=mapping_rules,
                target_schema=target_schema,
                required_fields=required_fields,
            )

        def safe_batch_transform_orders(
            order_dir: str,
            courier_name: str = "CJ대한통운",
            output_path: Optional[str] = None,
            template_path: Optional[str] = None,
        ) -> Any:
            """지정된 폴더 내의 모든 다채널 주문 엑셀 파일들을 읽어 대상 택배사 송장 엑셀로 일괄 변환 및 생성합니다.
            
            Args:
                order_dir: 주문 엑셀 파일들이 있는 폴더 경로.
                courier_name: 변환할 대상 택배사 이름 (예: 'CJ대한통운', '우체국택배', '한진택배', '롯데택배', '로젠택배').
                output_path: 생성할 송장 엑셀 파일 경로.
                template_path: 자사 커스텀 템플릿 파일 경로.
            """
            self.permissions.check_permission("read_safe", target_path=order_dir)
            target = output_path or str(self.output_dir / f"{courier_name}_송장.xlsx")
            self.permissions.check_permission("create_file", target_path=target)
            return batch_transform_orders(
                order_dir=order_dir,
                courier_name=courier_name,
                output_path=target,
                template_path=template_path,
            )

        self.registry.register(safe_scan_directory, name="scan_directory")
        self.registry.register(safe_read_file, name="read_file")
        self.registry.register(safe_write_file, name="write_file")
        self.registry.register(safe_create_excel, name="create_excel")
        self.registry.register(safe_analyze_document, name="analyze_document")
        self.registry.register(safe_batch_analyze_documents, name="batch_analyze_documents")
        self.registry.register(safe_capture_screen, name="capture_screen")
        self.registry.register(safe_inspect_excel, name="inspect_excel")
        self.registry.register(safe_get_courier_preset, name="get_courier_preset")
        self.registry.register(safe_get_courier_preset, name="get_courier_standard_preset")
        self.registry.register(safe_transform_excel, name="transform_excel")
        self.registry.register(safe_transform_excel, name="transform_excel_to_standard")
        self.registry.register(safe_transform_excel, name="transform_order_excel")
        self.registry.register(safe_batch_transform_orders, name="batch_transform_orders")
        self.registry.register(safe_batch_transform_orders, name="transform_orders_to_invoice")

    def execute_instruction(
        self,
        instruction: str,
        auto_confirm: bool = False,
    ) -> Dict[str, Any]:
        """Execute natural language instruction via True Autonomous LLM Brain."""
        logger.info(f"Agent executing instruction: '{instruction}'")
        self.killswitch.check_emergency_stop()

        # Initialize dedicated session logger for this command
        session_logger = SessionLogger(instruction=instruction, log_dir=self.log_dir)
        self.agent.session_logger = session_logger

        # Execute ReAct Agent Loop
        agent_report = self.agent.run(instruction)

        # Print final report to CLI
        report_with_log = f"{agent_report}\n\n[dim]📄 세션 실행 로그: {session_logger.log_file}[/]"
        self.cli.print_success("JARVIS 자율 작업 완료", report_with_log)

        return {
            "success": True,
            "report": agent_report,
            "log_path": str(session_logger.log_file),
        }


def main():
    """Main CLI Entrypoint."""
    setup_logger(log_level="INFO")
    cli = JarvisCLI()
    cli.print_banner()

    pipeline = JarvisPipeline()
    try:
        from rich.prompt import Prompt
        user_input = Prompt.ask("\n[bold yellow]👉 수행할 작업을 자연어로 지시해주세요[/]")
        if user_input.strip():
            pipeline.execute_instruction(user_input)
    except KeyboardInterrupt:
        print("\n사용자에 의해 프로그램이 종료되었습니다.")
    except EmergencyStopException as e:
        cli.print_error("긴급 중단", str(e))
    except Exception as e:
        cli.print_error("작업 실패", str(e))


if __name__ == "__main__":
    main()
