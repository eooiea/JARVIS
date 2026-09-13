"""Unit tests for ShadowWorkspace and File Transaction Staging Manager (TDD)."""

import os
import shutil
import tempfile
from pathlib import Path
import pytest

from jarvis.infra.staging import ShadowWorkspace


class TestShadowWorkspace:
    """Test suite for Shadow Staging workspace isolation and atomic commit/discard."""

    @pytest.fixture
    def workspace_setup(self):
        """Create temporary real workspace and base staging root."""
        temp_dir = tempfile.mkdtemp(prefix="jarvis_test_ws_")
        real_ws = Path(temp_dir) / "real_project"
        real_ws.mkdir()
        staging_base = Path(temp_dir) / "staging_base"
        staging_base.mkdir()

        yield real_ws, staging_base

        # Cleanup
        shutil.rmtree(temp_dir, ignore_errors=True)

    def test_staging_initialization(self, workspace_setup):
        real_ws, staging_base = workspace_setup
        sw = ShadowWorkspace(task_id="task_001", staging_base_dir=str(staging_base))

        assert Path(sw.staging_dir).exists()
        assert "task_001" in sw.staging_dir

    def test_in_staging_context_manager(self, workspace_setup):
        real_ws, staging_base = workspace_setup
        sw = ShadowWorkspace(task_id="task_002", staging_base_dir=str(staging_base))
        original_cwd = os.getcwd()

        with sw.in_staging():
            current_cwd = os.getcwd()
            assert os.path.samefile(current_cwd, sw.staging_dir)
            # Create a file inside staging CWD
            with open("temp_output.txt", "w", encoding="utf-8") as f:
                f.write("Staging isolated content")

        # CWD restored
        assert os.path.samefile(os.getcwd(), original_cwd)
        # Verify file is inside staging
        assert (Path(sw.staging_dir) / "temp_output.txt").exists()
        # Verify file is NOT in real workspace
        assert not (real_ws / "temp_output.txt").exists()

    def test_commit_to_workspace(self, workspace_setup):
        real_ws, staging_base = workspace_setup
        sw = ShadowWorkspace(task_id="task_003", staging_base_dir=str(staging_base))

        # Create nested file in staging
        sub_dir = Path(sw.staging_dir) / "reports"
        sub_dir.mkdir(parents=True)
        sample_file = sub_dir / "summary.xlsx"
        sample_file.write_bytes(b"EXCEL_BINARY_MOCK_DATA_12345")

        # Commit to real workspace
        artifacts = sw.commit_to_workspace(target_workspace=str(real_ws))

        # Verify artifacts metadata
        assert len(artifacts) == 1
        art = artifacts[0]
        assert "summary.xlsx" in art.path
        assert art.size_bytes == len(b"EXCEL_BINARY_MOCK_DATA_12345")
        assert len(art.sha256) == 64  # valid sha256 hex string

        # Verify file exists in real workspace
        committed_file = real_ws / "reports" / "summary.xlsx"
        assert committed_file.exists()
        assert committed_file.read_bytes() == b"EXCEL_BINARY_MOCK_DATA_12345"

    def test_discard_cleans_up_staging(self, workspace_setup):
        real_ws, staging_base = workspace_setup
        sw = ShadowWorkspace(task_id="task_004", staging_base_dir=str(staging_base))

        # Create a dirty file in staging
        dirty_file = Path(sw.staging_dir) / "corrupt_data.csv"
        dirty_file.write_text("corrupted,broken", encoding="utf-8")

        # Discard staging
        sw.discard()

        # Staging folder should be completely deleted
        assert not Path(sw.staging_dir).exists()
        # Real workspace remains clean
        assert not (real_ws / "corrupt_data.csv").exists()
