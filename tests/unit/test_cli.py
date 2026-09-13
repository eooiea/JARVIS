"""Unit tests for JARVIS Rich CLI interface (TDD)."""

import pytest
from jarvis.cli.app import JarvisCLI
from jarvis.brain.planner import TaskPlanner


def test_cli_print_banner():
    """JarvisCLI print_banner should execute without MarkupError."""
    cli = JarvisCLI()
    # Should execute smoothly without raising any Rich markup exceptions
    cli.print_banner()


def test_cli_render_plan():
    """JarvisCLI render_plan should render task plan tables without exceptions."""
    cli = JarvisCLI()
    planner = TaskPlanner()
    plan = planner.create_plan("영수증 캡처해서 엑셀로 만들어줘")
    
    cli.render_plan(plan)
