"""File Manager for unified outputs path and duplicate numbering protection."""

from pathlib import Path
from typing import Optional
from jarvis.utils.config import JarvisConfig, load_config
from jarvis.utils.logger import get_logger

logger = get_logger("office.file_manager")


class FileManager:
    """Manages output paths, unified directories, and duplicate file numbering."""

    def __init__(self, output_dir: Optional[Path | str] = None, config: Optional[JarvisConfig] = None):
        if output_dir:
            self.output_dir = Path(output_dir).resolve()
        else:
            cfg = config or load_config()
            self.output_dir = cfg.get_output_path()

        self.output_dir.mkdir(parents=True, exist_ok=True)

    def get_unique_filepath(self, filename: str) -> Path:
        """Return non-existing Path by appending incrementing numbering suffix (e.g. file_(1).xlsx)."""
        target_path = self.output_dir / filename
        if not target_path.exists():
            return target_path

        stem = target_path.stem
        suffix = target_path.suffix
        counter = 1

        while True:
            candidate_name = f"{stem}_({counter}){suffix}"
            candidate_path = self.output_dir / candidate_name
            if not candidate_path.exists():
                logger.info(f"Resolved duplicate filename: {filename} -> {candidate_name}")
                return candidate_path
            counter += 1
