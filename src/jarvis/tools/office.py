"""Smart Office Tools for styled spreadsheet creation and reporting."""

from pathlib import Path
from typing import Union, List, Dict, Any, Optional
from jarvis.office.excel_writer import ExcelWriter
from jarvis.office.file_manager import FileManager
from jarvis.utils.logger import get_logger

logger = get_logger("tools.office")


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
