"""Configuration Loader and Pydantic Schemas for JARVIS."""

import os
from pathlib import Path
from typing import Optional
import yaml
from dotenv import load_dotenv
from pydantic import BaseModel, Field


class SystemConfig(BaseModel):
    name: str = "JARVIS"
    output_dir: str = "outputs"
    log_level: str = "INFO"


class GeminiConfig(BaseModel):
    model: str = "gemini-2.5-flash"
    complex_model: str = "gemini-2.5-pro"
    temperature: float = 0.2


class OllamaConfig(BaseModel):
    host: str = "http://localhost:11434"
    model: str = "qwen2.5:14b"
    vision_model: str = "llava-llama3:latest"
    temperature: float = 0.2


class LLMConfig(BaseModel):
    default_provider: str = "gemini"
    gemini: GeminiConfig = Field(default_factory=GeminiConfig)
    ollama: OllamaConfig = Field(default_factory=OllamaConfig)


class ControllerConfig(BaseModel):
    action_delay: float = 0.2
    failsafe: bool = True
    killswitch_key: str = "ctrl+alt+s"


class OfficeConfig(BaseModel):
    default_sheet_name: str = "Data"
    auto_numbering: bool = True


class BacktrackingConfig(BaseModel):
    staging_dir: str = ".jarvis/staging"
    max_retries_per_branch: int = 2
    total_retry_budget: int = 5


class JarvisConfig(BaseModel):
    system: SystemConfig = Field(default_factory=SystemConfig)
    llm: LLMConfig = Field(default_factory=LLMConfig)
    controller: ControllerConfig = Field(default_factory=ControllerConfig)
    office: OfficeConfig = Field(default_factory=OfficeConfig)
    backtracking: BacktrackingConfig = Field(default_factory=BacktrackingConfig)
    gemini_api_key: Optional[str] = None
    project_root: Optional[Path] = None

    def get_output_path(self) -> Path:
        """Resolve output directory, create if not exists, and return absolute Path."""
        root = self.project_root or Path.cwd()
        out_dir = root / self.system.output_dir
        out_dir.mkdir(parents=True, exist_ok=True)
        return out_dir


def load_config(config_path: Optional[Path | str] = None) -> JarvisConfig:
    """Load configuration from YAML file and environment variables."""
    # Find project root
    current_file = Path(__file__).resolve()
    # src/jarvis/utils/config.py -> root is 4 levels up
    project_root = current_file.parent.parent.parent.parent

    # Load .env file
    env_file = project_root / ".env"
    if env_file.exists():
        load_dotenv(dotenv_path=env_file)
    else:
        # Also check config/.env
        config_env = project_root / "config" / ".env"
        if config_env.exists():
            load_dotenv(dotenv_path=config_env)
        else:
            load_dotenv()

    # Determine config.yaml path
    if config_path is None:
        default_config = project_root / "config" / "config.yaml"
        if default_config.exists():
            resolved_path = default_config
        else:
            resolved_path = Path("config.yaml")
    else:
        resolved_path = Path(config_path)

    raw_data = {}
    if resolved_path.exists():
        with open(resolved_path, "r", encoding="utf-8") as f:
            raw_data = yaml.safe_load(f) or {}

    config = JarvisConfig(**raw_data)
    config.gemini_api_key = os.getenv("GEMINI_API_KEY")
    config.project_root = project_root

    return config
