"""AI and rule-based filename generator for extracted documents."""

import re
from datetime import datetime
from typing import Dict, Any, Optional
from jarvis.utils.logger import get_logger

logger = get_logger("office.file_namer")


class FileNamer:
    """Generates context-aware, sanitized filenames based on document metadata."""

    def __init__(self):
        pass

    def _sanitize_filename(self, name: str) -> str:
        """Remove characters invalid in Windows filenames."""
        sanitized = re.sub(r'[\\/*?:"<>|]', "_", name)
        sanitized = re.sub(r"\s+", "_", sanitized).strip("._")
        return sanitized or "문서"

    def generate_filename(
        self,
        data: Dict[str, Any],
        default_prefix: str = "문서_정리",
        extension: str = "xlsx",
    ) -> str:
        """Generate formatted filename like '20260902_식대영수증_정리.xlsx'."""
        date_str = data.get("date") or datetime.now().strftime("%Y%m%d")
        # Clean date string (remove dashes or slashes for filename)
        date_part = re.sub(r"\D", "", str(date_str))[:8] or datetime.now().strftime("%Y%m%d")

        title_part = data.get("title") or data.get("doc_type") or default_prefix
        clean_title = self._sanitize_filename(str(title_part))

        ext = extension.lstrip(".")
        filename = f"{date_part}_{clean_title}.{ext}"
        logger.info(f"Generated filename: {filename}")
        return filename
