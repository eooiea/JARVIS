"""CSV and TSV export/import handler with automatic Korean encoding detection."""

import csv
from pathlib import Path
from typing import List, Dict, Any, Union
from jarvis.utils.logger import get_logger

logger = get_logger("office.csv_handler")


class CSVHandler:
    """Handles CSV/TSV input and output with UTF-8-SIG (Excel compatible) and CP949 fallbacks."""

    def __init__(self):
        pass

    def export_csv(
        self,
        data: List[Dict[str, Any]],
        output_path: Union[Path, str],
        delimiter: str = ",",
        encoding: str = "utf-8-sig",
    ) -> Path:
        """Export list of row dictionaries to CSV file."""
        out_file = Path(output_path).resolve()
        out_file.parent.mkdir(parents=True, exist_ok=True)

        if not data:
            data = [{"내용": "데이터 없음"}]

        headers = list(data[0].keys())

        with open(out_file, "w", newline="", encoding=encoding) as f:
            writer = csv.DictWriter(f, fieldnames=headers, delimiter=delimiter)
            writer.writeheader()
            writer.writerows(data)

        logger.info(f"Exported CSV file: {out_file} ({len(data)} rows)")
        return out_file

    def read_csv(
        self,
        file_path: Union[Path, str],
        delimiter: str = ",",
    ) -> List[Dict[str, Any]]:
        """Read CSV file with automatic encoding fallback (utf-8-sig -> utf-8 -> cp949)."""
        path = Path(file_path).resolve()
        if not path.exists():
            raise FileNotFoundError(f"[CSV 파일을 찾을 수 없습니다: {path}]")

        encodings = ["utf-8-sig", "utf-8", "cp949", "euc-kr"]
        for enc in encodings:
            try:
                with open(path, "r", newline="", encoding=enc) as f:
                    reader = csv.DictReader(f, delimiter=delimiter)
                    rows = [dict(row) for row in reader]
                    logger.info(f"Read CSV ({enc}): {path.name} ({len(rows)} rows)")
                    return rows
            except (UnicodeDecodeError, UnicodeError):
                continue

        raise ValueError(f"[인코딩 오류] CSV 파일({path.name})을 읽을 수 없습니다.")
