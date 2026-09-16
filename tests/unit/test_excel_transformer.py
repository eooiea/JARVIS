"""Unit tests for ExcelTransformer and scenario 1 office tools."""

import pytest
import openpyxl
from pathlib import Path
from jarvis.office.excel_transformer import (
    ExcelTransformer,
    get_courier_standard_preset,
    normalize_phone_number,
    normalize_quantity,
    clean_address,
)
from jarvis.tools.office import inspect_excel, get_courier_preset, transform_excel


@pytest.fixture
def sample_excel_file(tmp_path: Path) -> Path:
    """Create a sample order Excel file for testing."""
    file_path = tmp_path / "쿠팡_주문_테스트.xlsx"
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "주문목록"
    
    headers = ["받는사람", "수하인전화번호", "수하인주소", "등록상품명", "구매수량(개)", "배송메세지"]
    ws.append(headers)
    
    rows = [
        ["홍길동", "010.1234.5678", "서울시 서초구 강남대로 100 3층", "캠핑 텐트", "2개", "문 앞"],
        ["성춘향", "01098765432", "경기도 수원시 팔달구 매산로 1", "캠핑 의자", 1, ""],
        ["이몽룡", "010-1111-2222", "전북 남원시 요천로 123", "침낭", "3", None],
    ]
    for r in rows:
        ws.append(r)
        
    wb.save(file_path)
    return file_path


@pytest.fixture
def split_address_excel(tmp_path: Path) -> Path:
    """Create a sample order with split address columns (like Naver Smartstore)."""
    file_path = tmp_path / "스마트스토어_테스트.xlsx"
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "발주목록"
    
    headers = ["수취인명", "연락처1", "기본배송지", "상세배송지", "상품명", "수량", "배송메모"]
    ws.append(headers)
    
    rows = [
        ["임꺽정", "010-3333-4444", "강원도 춘천시 중앙로 1", "101호", "바베큐 그릴", 1, "경비실에 보관"],
    ]
    for r in rows:
        ws.append(r)
        
    wb.save(file_path)
    return file_path


def test_normalize_phone_number():
    assert normalize_phone_number("010.1234.5678") == "010-1234-5678"
    assert normalize_phone_number("01012345678") == "010-1234-5678"
    assert normalize_phone_number("010-1234-5678") == "010-1234-5678"
    assert normalize_phone_number("02-123-4567") == "02-123-4567"
    assert normalize_phone_number("021234567") == "02-123-4567"
    assert normalize_phone_number("0504-1234-5678") == "0504-1234-5678"
    assert normalize_phone_number("") == ""


def test_normalize_quantity():
    assert normalize_quantity("2개") == 2
    assert normalize_quantity("3EA") == 3
    assert normalize_quantity(4) == 4
    assert normalize_quantity("5") == 5
    assert normalize_quantity(None) == 1
    assert normalize_quantity("") == 1


def test_clean_address():
    assert clean_address("서울시  강남구   테헤란로 123 ") == "서울시 강남구 테헤란로 123"
    assert clean_address(["서울시 강남구", "테헤란로 123", "401호"]) == "서울시 강남구 테헤란로 123 401호"


def test_get_courier_standard_preset():
    cj = get_courier_standard_preset("CJ대한통운")
    assert "받는분성명" in cj["target_schema"]
    assert "전화번호1" in cj["target_schema"]
    assert "배송지주소" in cj["target_schema"]

    epost = get_courier_standard_preset("우체국택배")
    assert "수취인명" in epost["target_schema"]
    assert "수취인이동통신" in epost["target_schema"]
    assert "수취인주소" in epost["target_schema"]

    hanjin = get_courier_standard_preset("한진택배")
    assert "받는사람" in hanjin["target_schema"]

    lotte = get_courier_standard_preset("롯데택배")
    assert "수하인명" in lotte["target_schema"]

    logen = get_courier_standard_preset("로젠택배")
    assert "성명" in logen["target_schema"]


def test_inspect_excel_tool(sample_excel_file: Path):
    result = inspect_excel(str(sample_excel_file), max_sample_rows=1)
    assert result["file_name"] == "쿠팡_주문_테스트.xlsx"
    assert "받는사람" in result["headers"]
    assert len(result["sample_rows"]) == 1
    assert result["sample_rows"][0]["받는사람"] == "홍길동"
    assert result["total_rows"] == 3


def test_transform_excel_cj_success(sample_excel_file: Path):
    mapping_rules = {
        "받는사람": "받는분성명",
        "수하인전화번호": "전화번호1",
        "수하인주소": "배송지주소",
        "등록상품명": "품목명",
        "구매수량(개)": "수량",
        "배송메세지": "배송메시지",
    }
    target_schema = ["받는분성명", "전화번호1", "배송지주소", "품목명", "수량", "배송메시지"]
    
    result = transform_excel(
        source_path=str(sample_excel_file),
        mapping_rules=mapping_rules,
        target_schema=target_schema,
    )
    assert result["success"] is True
    assert result["count"] == 3
    assert len(result["rows"]) == 3
    
    row1 = result["rows"][0]
    assert row1["받는분성명"] == "홍길동"
    assert row1["전화번호1"] == "010-1234-5678"
    assert row1["수량"] == 2
    assert row1["배송메시지"] == "문 앞"

    row2 = result["rows"][1]
    assert row2["전화번호1"] == "010-9876-5432"


def test_transform_excel_split_address_success(split_address_excel: Path):
    mapping_rules = {
        "수취인명": "받는분성명",
        "연락처1": "전화번호1",
        "기본배송지": "배송지주소",
        "상세배송지": "배송지주소",  # Hybrid merge to same target column
        "상품명": "품목명",
        "수량": "수량",
        "배송메모": "배송메시지",
    }
    target_schema = ["받는분성명", "전화번호1", "배송지주소", "품목명", "수량", "배송메시지"]
    
    result = transform_excel(
        source_path=str(split_address_excel),
        mapping_rules=mapping_rules,
        target_schema=target_schema,
    )
    assert result["success"] is True
    assert result["count"] == 1
    assert result["rows"][0]["배송지주소"] == "강원도 춘천시 중앙로 1 101호"


def test_transform_excel_schema_validation_error(sample_excel_file: Path):
    # Intentional omission of '받는분성명'
    mapping_rules = {
        "수하인전화번호": "전화번호1",
        "수하인주소": "배송지주소",
        "등록상품명": "품목명",
    }
    target_schema = ["받는분성명", "전화번호1", "배송지주소", "품목명", "수량", "배송메시지"]
    required_fields = ["받는분성명", "전화번호1", "배송지주소"]
    
    result = transform_excel(
        source_path=str(sample_excel_file),
        mapping_rules=mapping_rules,
        target_schema=target_schema,
        required_fields=required_fields,
    )
    assert result["success"] is False
    assert result["error_type"] == "SchemaValidationError"
    assert "받는분성명" in result["missing_fields"]
    assert "hint" in result


def test_batch_transform_orders_all(tmp_path: Path):
    from jarvis.tools.office import batch_transform_orders
    from jarvis.office.excel_transformer import resolve_smart_path

    order_dir = Path("tests/data/scenario1/set01/orders")
    out_file = tmp_path / "CJ대한통운_송장양식.xlsx"

    res = batch_transform_orders(
        order_dir=str(order_dir),
        courier_name="CJ대한통운",
        output_path=str(out_file),
    )
    assert res["success"] is True
    assert res["total_orders"] == 11
    assert out_file.exists()

    # Verify smart path typo resilience
    typo_path = order_dir / "지마arket_주문.xlsx"
    resolved = resolve_smart_path(typo_path)
    assert resolved.name == "지마켓_주문.xlsx"

