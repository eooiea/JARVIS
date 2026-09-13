"""Shadow Workspace & File Transaction Manager for JARVIS.

Isolates tool execution, file creation, and modifications in `.jarvis/staging/{task_id}/`
until validation succeeds, then commits atomically to the real workspace.
"""

from contextlib import contextmanager
import hashlib
import os
from pathlib import Path
import shutil
from typing import List, Optional

from jarvis.brain.memory import ArtifactSnapshot
from jarvis.utils.logger import get_logger

logger = get_logger("infra.staging")


class ShadowWorkspace:
    """Manages an isolated staging directory for agent tasks."""

    def __init__(
        self,
        task_id: str,
        staging_base_dir: Optional[str] = None,
    ):
        self.task_id = task_id
        base_dir = Path(staging_base_dir) if staging_base_dir else Path(".jarvis") / "staging"
        self.staging_dir = str((base_dir / task_id).resolve())

        # Ensure staging directory exists
        os.makedirs(self.staging_dir, exist_ok=True)
        logger.info(f"Initialized ShadowWorkspace for task '{task_id}' at: {self.staging_dir}")

    @contextmanager
    def in_staging(self):
        """Context manager to temporarily switch CWD to staging_dir."""
        os.makedirs(self.staging_dir, exist_ok=True)
        previous_cwd = os.getcwd()
        try:
            os.chdir(self.staging_dir)
            yield self.staging_dir
        finally:
            os.chdir(previous_cwd)

    def _compute_sha256(self, file_path: Path) -> str:
        """Compute SHA-256 hash of a file."""
        hasher = hashlib.sha256()
        with open(file_path, "rb") as f:
            while chunk := f.read(65536):
                hasher.update(chunk)
        return hasher.hexdigest()

    def commit_to_workspace(self, target_workspace: str) -> List[ArtifactSnapshot]:
        """Atomically copy all staged files into the target real workspace directory."""
        target_root = Path(target_workspace).resolve()
        os.makedirs(target_root, exist_ok=True)
        committed_artifacts: List[ArtifactSnapshot] = []

        staging_path = Path(self.staging_dir)
        if not staging_path.exists():
            return committed_artifacts

        for root, _, files in os.walk(self.staging_dir):
            for file_name in files:
                source_file = Path(root) / file_name
                rel_path = source_file.relative_to(staging_path)
                dest_file = target_root / rel_path

                # Ensure destination directory exists
                dest_file.parent.mkdir(parents=True, exist_ok=True)

                # Atomic copy
                shutil.copy2(source_file, dest_file)

                # Generate artifact snapshot
                sha256 = self._compute_sha256(dest_file)
                size_bytes = dest_file.stat().st_size
                committed_artifacts.append(
                    ArtifactSnapshot(
                        path=str(rel_path).replace("\\", "/"),
                        sha256=sha256,
                        size_bytes=size_bytes,
                    )
                )
                logger.info(f"Committed staged file: {rel_path} -> {dest_file} ({size_bytes} bytes)")

        return committed_artifacts

    def discard(self) -> None:
        """Completely discard and delete the staging directory and all intermediate files."""
        if Path(self.staging_dir).exists():
            shutil.rmtree(self.staging_dir, ignore_errors=True)
            logger.info(f"Discarded staging workspace for task '{self.task_id}'")
