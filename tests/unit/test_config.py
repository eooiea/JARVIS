"""Unit tests for JARVIS Configuration Loader (TDD)."""

import os
import pytest
from pathlib import Path
from jarvis.utils.config import load_config, JarvisConfig, SystemConfig, LLMConfig, ControllerConfig, OfficeConfig


def test_default_config_loading(tmp_path: Path):
    """Test loading configuration from default or custom yaml file."""
    yaml_content = """
system:
  name: "TEST_JARVIS"
  output_dir: "custom_outputs"
  log_level: "DEBUG"
llm:
  default_provider: "ollama"
  gemini:
    model: "gemini-2.5-flash"
  ollama:
    host: "http://localhost:11434"
    model: "qwen2.5:14b"
controller:
  action_delay: 0.5
  failsafe: true
  killswitch_key: "ctrl+alt+s"
office:
  default_sheet_name: "TestSheet"
  auto_numbering: true
"""
    config_file = tmp_path / "test_config.yaml"
    config_file.write_text(yaml_content, encoding="utf-8")

    cfg = load_config(config_path=config_file)
    assert isinstance(cfg, JarvisConfig)
    assert cfg.system.name == "TEST_JARVIS"
    assert cfg.system.output_dir == "custom_outputs"
    assert cfg.system.log_level == "DEBUG"
    assert cfg.llm.default_provider == "ollama"
    assert cfg.llm.ollama.model == "qwen2.5:14b"
    assert cfg.controller.action_delay == 0.5
    assert cfg.office.default_sheet_name == "TestSheet"


def test_env_var_gemini_api_key_injection(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """Test that GEMINI_API_KEY from environment variables is properly injected."""
    test_key = "AIzaSyTestApiKey123456"
    monkeypatch.setenv("GEMINI_API_KEY", test_key)

    yaml_content = """
system:
  name: "JARVIS"
"""
    config_file = tmp_path / "config.yaml"
    config_file.write_text(yaml_content, encoding="utf-8")

    cfg = load_config(config_path=config_file)
    assert cfg.gemini_api_key == test_key


def test_output_path_resolution(tmp_path: Path):
    """Test get_output_path method creates and returns absolute Path."""
    yaml_content = """
system:
  output_dir: "my_test_outputs"
"""
    config_file = tmp_path / "config.yaml"
    config_file.write_text(yaml_content, encoding="utf-8")

    cfg = load_config(config_path=config_file)
    out_path = cfg.get_output_path()
    assert isinstance(out_path, Path)
    assert out_path.name == "my_test_outputs"
