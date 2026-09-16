"""Smart Office Tools for styled spreadsheet creation, inspection, and transformation."""

from pathlib import Path
from typing import Union, List, Dict, Any, Optional
from jarvis.office.excel_writer import ExcelWriter
from jarvis.office.excel_transformer import (
    ExcelTransformer,
    get_courier_standard_preset,
    batch_transform_orders as _batch_transform_orders,
)
from jarvis.office.file_manager import FileManager
from jarvis.utils.logger import get_logger

logger = get_logger("tools.office")

_transformer = ExcelTransformer()


def batch_transform_orders(
    order_dir: str,
    courier_name: str = "CJ대한통운",
    output_path: Optional[str] = None,
    template_path: Optional[str] = None,
) -> Dict[str, Any]:
    """지정된 폴더 내의 모든 오픈마켓 주문 엑셀(.xlsx) 파일들을 읽어서 지정된 택배사 또는 커스텀 템플릿 표준 송장 엑셀로 일괄 변환 및 생성합니다.

    - 국내 5대 택배사(CJ대한통운, 우체국, 한진, 롯데, 로젠) 및 자사 커스텀 템플릿 지원
    - 전화번호 표준화, 주소 결합, 품목 및 수량 정수 변환 자동 처리
    - 주문 건수 1:1 보존 보장

    Args:
        order_dir: 주문서 파일들이 위치한 폴더 경로 (예: 'orders/').
        courier_name: 변환할 대상 택배사 이름 (예: 'CJ대한통운', '우체국택배', '한진택배', '롯데택배', '로젠택배').
        output_path: 생성할 최종 송장 엑셀 파일 경로 (생략 시 outputs/ 폴더에 자동 생성).
        template_path: 자사 커스텀 템플릿 엑셀 경로 (사용자 양식 변환 시 사용).
    """
    target_out = output_path or f"outputs/{courier_name}_송장양식.xlsx"
    return _batch_transform_orders(
        order_dir=order_dir,
        courier_name=courier_name,
        output_path=target_out,
        template_path=template_path,
    )



def inspect_excel(
    file_path: str,
    max_sample_rows: int = 1,
) -> Dict[str, Any]:
    """엑셀 파일의 시트명, 컬럼 헤더 목록, 샘플 데이터를 최소 토큰으로 신속히 조회합니다.

    Args:
        file_path: 조회할 엑셀(.xlsx) 파일 경로.
        max_sample_rows: 미리보기할 샘플 행 수 (기본 1).
    """
    return _transformer.inspect(file_path=file_path, max_sample_rows=max_sample_rows)


def get_courier_preset(
    courier_name: str,
) -> Dict[str, Any]:
    """국내 5대 택배사(CJ대한통운, 우체국택배, 한진택배, 롯데택배, 로젠택배)의 표준 헤더 스키마와 필수 필드 규격을 조회합니다.

    Args:
        courier_name: 택배사 명칭 (예: 'CJ대한통운', '우체국', '한진', '롯데', '로젠').
    """
    return get_courier_standard_preset(courier_name=courier_name)


def transform_excel(
    source_path: str,
    mapping_rules: Dict[str, Any],
    target_schema: Optional[List[str]] = None,
    required_fields: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """소스 엑셀 데이터를 매핑 규칙에 따라 타깃 헤더 스키마로 정규화 및 변환합니다.

    - 1:1 매핑 및 다중 컬럼 결합(주소 분리형 등) 지원
    - 전화번호(010-XXXX-XXXX), 수량(int), 주소 공백 정제 자동 처리
    - 필수 타깃 필드 누락 시 구체적인 에러 및 자가 수정 힌트 반환

    Args:
        source_path: 변환할 원본 엑셀 파일 경로.
        mapping_rules: 소스 컬럼 -> 타깃 컬럼 매핑 규칙 (예: {"받는사람": "받는분성명", "기본배송지": "배송지주소", "상세배송지": "배송지주소"}).
        target_schema: 결과 엑셀에 포함될 컬럼명 순서 리스트.
        required_fields: 누락 시 에러를 발생시킬 필수 필드 목록 (생략 시 자동 산출).
    """
    return _transformer.transform(
        source_path=source_path,
        mapping_rules=mapping_rules,
        target_schema=target_schema,
        required_fields=required_fields,
    )


def create_excel(
    data: Union[Dict[str, Any], List[Dict[str, Any]]],
    output_path: Union[str, Path],
    sheet_name: str = "Data",
    auto_number: bool = True,
) -> Path:
    """Create a styled Excel spreadsheet from structured data with auto duplicate protection."""
    writer = ExcelWriter()
    target_path = Path(output_path).resolve()

    if auto_number:
        manager = FileManager(output_dir=target_path.parent)
        final_path = manager.get_unique_filepath(target_path.name)
    else:
        final_path = target_path

    return writer.create_styled_excel(
        data=data,
        output_path=final_path,
        sheet_name=sheet_name,
    )

