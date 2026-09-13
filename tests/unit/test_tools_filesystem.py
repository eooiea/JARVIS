"""Unit tests for JARVIS Filesystem Tools (TDD Red-Green)."""

import pytest
from pathlib import Path
from jarvis.tools.filesystem import scan_directory, read_file, write_file


def test_scan_directory_basic(tmp_path: Path):
    """scan_directory should return structured list of files and folders with metadata."""
    # Create test directory structure
    sub_dir = tmp_path / "sub_folder"
    sub_dir.mkdir()
    (tmp_path / "file1.txt").write_text("Hello World", encoding="utf-8")
    (sub_dir / "file2.py").write_text("print('test')", encoding="utf-8")

    # Hidden/ignored folder
    git_dir = tmp_path / ".git"
    git_dir.mkdir()
    (git_dir / "config").write_text("ignored", encoding="utf-8")

    items = scan_directory(tmp_path, recursive=True)

    assert len(items) >= 2
    names = [item["name"] for item in items]
    assert "file1.txt" in names
    assert "file2.py" in names
    assert "config" not in names  # .git should be ignored by default

    # Verify metadata fields
    first = items[0]
    assert "path" in first
    assert "type" in first  # "file" or "directory"
    assert "size_kb" in first or "size_bytes" in first
    assert "modified_time" in first


def test_scan_directory_nonexistent_raises():
    """scan_directory should raise FileNotFoundError for nonexistent path."""
    with pytest.raises(FileNotFoundError):
        scan_directory("C:/nonexistent_random_dir_12345")


def test_read_and_write_file(tmp_path: Path):
    """read_file and write_file should safely handle UTF-8 text files."""
    test_file = tmp_path / "test.txt"
    written_path = write_file(test_file, "안녕하세요 JARVIS")
    assert written_path.exists()

    content = read_file(test_file)
    assert content == "안녕하세요 JARVIS"
