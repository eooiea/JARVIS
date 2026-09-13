"""Unit tests for JARVIS Logger Utility (TDD)."""

import logging
from jarvis.utils.logger import get_logger, setup_logger


def test_get_logger_instance():
    """Test get_logger returns a configured Logger instance."""
    logger = get_logger("test_module")
    assert isinstance(logger, logging.Logger)
    assert logger.name == "jarvis.test_module"


def test_setup_logger_log_level():
    """Test setup_logger correctly applies log level."""
    logger = setup_logger(log_level="DEBUG")
    assert logger.level == logging.DEBUG
