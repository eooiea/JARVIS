"""Unit tests for JARVIS Tool Registry (TDD Red-Green)."""

import pytest
from jarvis.tools.registry import ToolRegistry


def sample_tool_fn(path: str, count: int = 1) -> str:
    """A sample tool for testing registry.
    
    Args:
        path: Path to inspect.
        count: Number of iterations.
    """
    return f"Processed {path} {count} times"


def test_tool_registry_registration_and_schema():
    """Registry should register functions and generate OpenAI/Gemini compatible tool definitions."""
    registry = ToolRegistry()
    registry.register(sample_tool_fn)

    schemas = registry.get_definitions()
    assert len(schemas) == 1
    tool_def = schemas[0]
    assert tool_def["name"] == "sample_tool_fn"
    assert "A sample tool for testing registry" in tool_def["description"]
    assert "properties" in tool_def["parameters"]
    assert "path" in tool_def["parameters"]["properties"]
    assert "count" in tool_def["parameters"]["properties"]


def test_tool_registry_execution():
    """Registry should execute registered tool with kwargs safely."""
    registry = ToolRegistry()
    registry.register(sample_tool_fn)

    result = registry.execute("sample_tool_fn", path="C:/test", count=3)
    assert result == "Processed C:/test 3 times"


def test_tool_registry_execution_error_handling():
    """Registry should return clean error string when tool execution fails instead of crashing."""
    registry = ToolRegistry()

    def error_tool():
        """A tool that raises an exception."""
        raise ValueError("Something went wrong!")

    registry.register(error_tool)
    result = registry.execute("error_tool")
    assert "Error executing error_tool" in result
    assert "Something went wrong!" in result


def test_tool_registry_validation_missing_required_arg():
    """Registry should fail pre-validation before execution if required argument is missing."""
    registry = ToolRegistry()
    registry.register(sample_tool_fn)

    # Missing required 'path'
    result = registry.execute("sample_tool_fn", count=3)
    assert "Validation Error:" in result
    assert "path" in result
    assert "required" in result.lower()


def test_tool_registry_validation_unexpected_arg():
    """Registry should fail pre-validation if unexpected argument is provided."""
    registry = ToolRegistry()
    registry.register(sample_tool_fn)

    result = registry.execute("sample_tool_fn", path="C:/test", invalid_key="val")
    assert "Validation Error:" in result
    assert "invalid_key" in result
    assert "unexpected" in result.lower()


def test_tool_registry_validation_type_mismatch():
    """Registry should fail pre-validation if argument type cannot be satisfied."""
    registry = ToolRegistry()
    registry.register(sample_tool_fn)

    # count expects int, give non-convertible string
    result = registry.execute("sample_tool_fn", path="C:/test", count="invalid_number")
    assert "Validation Error:" in result
    assert "count" in result
    assert "type" in result.lower()


def test_tool_registry_validate_args_direct():
    """validate_args should return None for valid args and error string for invalid args or tools."""
    registry = ToolRegistry()
    registry.register(sample_tool_fn)

    # Valid args
    assert registry.validate_args("sample_tool_fn", {"path": "C:/valid", "count": 2}) is None
    # Unregistered tool
    assert "not registered" in registry.validate_args("unknown_tool", {})


