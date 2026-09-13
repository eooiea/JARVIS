"""Filesystem tools for scanning, reading, and managing OS directory structures."""

import os
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional, Union
from jarvis.utils.logger import get_logger

logger = get_logger("tools.filesystem")

DEFAULT_EXCLUDE_DIRS = {".git", ".venv", "venv", "__pycache__", "node_modules", ".pytest_cache", ".idea", ".vscode"}


def scan_directory(
    path: Union[str, Path],
    recursive: bool = True,
    max_depth: int = 4,
    exclude_patterns: Optional[List[str]] = None,
) -> List[Dict[str, Any]]:
    """Scan local directory and return structured list of files and folders with metadata."""
    root_path = Path(path).resolve()
    if not root_path.exists():
        raise FileNotFoundError(f"[디렉터리를 찾을 수 없습니다: {root_path}]")

    exclude_set = DEFAULT_EXCLUDE_DIRS.copy()
    if exclude_patterns:
        exclude_set.update(exclude_patterns)

    results: List[Dict[str, Any]] = []

    def _format_size(size_bytes: int) -> str:
        if size_bytes < 1024:
            return f"{size_bytes} B"
        elif size_bytes < 1024 * 1024:
            return f"{size_bytes / 1024:.1f} KB"
        else:
            return f"{size_bytes / (1024 * 1024):.2f} MB"

    def _scan_recursive(current_dir: Path, current_depth: int):
        if current_depth > max_depth:
            return

        try:
            for item in sorted(current_dir.iterdir(), key=lambda p: (not p.is_dir(), p.name.lower())):
                # Skip excluded folders/files
                if item.name in exclude_set or item.name.startswith("."):
                    continue

                rel_path = str(item.relative_to(root_path))
                stat = item.stat()
                mod_time = datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M:%S")

                if item.is_dir():
                    # Count child items
                    try:
                        child_count = len([c for c in item.iterdir() if c.name not in exclude_set])
                    except Exception:
                        child_count = 0

                    results.append({
                        "name": item.name,
                        "relative_path": rel_path,
                        "type": "폴더",
                        "size": f"{child_count}개 항목",
                        "size_bytes": 0,
                        "child_count": child_count,
                        "modified_time": mod_time,
                        "path": str(item),
                    })

                    if recursive:
                        _scan_recursive(item, current_depth + 1)
                else:
                    results.append({
                        "name": item.name,
                        "relative_path": rel_path,
                        "type": "파일",
                        "size": _format_size(stat.st_size),
                        "size_bytes": stat.st_size,
                        "extension": item.suffix.lower(),
                        "modified_time": mod_time,
                        "path": str(item),
                    })
        except PermissionError:
            logger.warning(f"Permission denied accessing directory: {current_dir}")

    _scan_recursive(root_path, current_depth=1)
    logger.info(f"Scanned directory '{root_path.name}': {len(results)} items found.")
    return results


def read_file(path: Union[str, Path], encoding: str = "utf-8") -> str:
    """Read and return content of a local file."""
    file_path = Path(path).resolve()
    if not file_path.exists():
        raise FileNotFoundError(f"[파일을 찾을 수 없습니다: {file_path}]")
    return file_path.read_text(encoding=encoding, errors="replace")


def write_file(path: Union[str, Path], content: str, encoding: str = "utf-8") -> Path:
    """Write text content to a local file."""
    file_path = Path(path).resolve()
    file_path.parent.mkdir(parents=True, exist_ok=True)
    file_path.write_text(content, encoding=encoding)
    logger.info(f"Saved file: {file_path} ({len(content)} chars)")
    return file_path
