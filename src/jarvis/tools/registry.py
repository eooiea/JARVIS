"""Tool Registry for registering functions and exporting Function Calling schemas."""

import inspect
import json
import types
from typing import Callable, Dict, Any, List, Optional, Union, get_args
from jarvis.utils.logger import get_logger

logger = get_logger("tools.registry")


class ToolRegistry:
    """Central registry of tools with automatic JSON Schema generation."""

    def __init__(self):
        self._tools: Dict[str, Callable] = {}
        self._definitions: Dict[str, Dict[str, Any]] = {}

    def register(self, fn: Callable, name: Optional[str] = None, description: Optional[str] = None):
        """Register a Python callable and generate its Function Calling schema."""
        tool_name = name or fn.__name__
        doc = description or (fn.__doc__ or "").strip()
        sig = inspect.signature(fn)

        properties: Dict[str, Any] = {}
        required: List[str] = []

        type_map = {
            str: "string",
            int: "integer",
            float: "number",
            bool: "boolean",
            list: "array",
            dict: "object",
        }

        for param_name, param in sig.parameters.items():
            if param_name in ("self", "cls"):
                continue

            param_type: Any = "string"
            if param.annotation in (Any, object, inspect.Parameter.empty):
                param_type = "any"
            elif param.annotation != inspect.Parameter.empty:
                origin = getattr(param.annotation, "__origin__", param.annotation)
                if origin in (Union, getattr(types, "UnionType", None)):
                    union_args = get_args(param.annotation)
                    extracted_types = []
                    for arg in union_args:
                        arg_origin = getattr(arg, "__origin__", arg)
                        if arg_origin in type_map:
                            extracted_types.append(type_map[arg_origin])
                    if extracted_types:
                        param_type = extracted_types if len(extracted_types) > 1 else extracted_types[0]
                    else:
                        param_type = "any"
                else:
                    param_type = type_map.get(origin, "string")

            properties[param_name] = {
                "type": param_type,
                "description": f"Parameter {param_name}",
            }

            if param.default == inspect.Parameter.empty:
                required.append(param_name)

        tool_def = {
            "name": tool_name,
            "description": doc.split("\n\n")[0] if doc else f"Tool {tool_name}",
            "parameters": {
                "type": "object",
                "properties": properties,
                "required": required,
            },
        }

        self._tools[tool_name] = fn
        self._definitions[tool_name] = tool_def
        logger.debug(f"Registered tool: {tool_name}")

    def get_definitions(self) -> List[Dict[str, Any]]:
        """Return list of tool schemas for LLM tool calling."""
        return list(self._definitions.values())

    def validate_args(self, name: str, args: Dict[str, Any]) -> Optional[str]:
        """Pre-validate arguments against tool schema before execution.
        
        Returns None if valid, or an error description string if invalid.
        """
        if name not in self._tools:
            return f"Tool '{name}' is not registered."

        tool_def = self._definitions.get(name, {})
        parameters = tool_def.get("parameters", {})
        required = parameters.get("required", [])
        properties = parameters.get("properties", {})

        # 1. Check for missing required parameters
        missing = [r for r in required if r not in args]
        if missing:
            return f"Tool '{name}' missing required argument(s): {', '.join(missing)}."

        # 2. Check for unexpected parameters
        unexpected = [k for k in args if k not in properties]
        if unexpected:
            return f"Tool '{name}' received unexpected argument(s): {', '.join(unexpected)}."

        # 3. Check parameter types
        def matches_type(t: str, v: Any) -> bool:
            if t == "string":
                return isinstance(v, str)
            elif t == "integer":
                return not isinstance(v, bool) and (
                    isinstance(v, int) or (isinstance(v, str) and v.lstrip("-").isdigit())
                )
            elif t == "number":
                if isinstance(v, bool):
                    return False
                if isinstance(v, (int, float)):
                    return True
                try:
                    float(v)
                    return True
                except (ValueError, TypeError):
                    return False
            elif t == "boolean":
                return isinstance(v, bool) or str(v).lower() in ("true", "false")
            elif t == "array":
                return isinstance(v, (list, tuple))
            elif t == "object":
                return isinstance(v, dict)
            return True

        for key, val in args.items():
            if key not in properties:
                continue
            if val is None and key not in required:
                continue
            raw_expected = properties[key].get("type", "string")
            expected_types = raw_expected if isinstance(raw_expected, list) else [raw_expected]

            if not any(matches_type(t, val) for t in expected_types):
                expected_desc = " or ".join(expected_types)
                return f"Argument '{key}' for tool '{name}' expected type '{expected_desc}', got '{type(val).__name__}'."

        return None


    def execute(self, name: str, **kwargs) -> Any:
        """Execute a registered tool safely with pre-validation and return output."""
        if name not in self._tools:
            return f"Error: Tool '{name}' is not registered."

        # Pre-validate arguments
        val_error = self.validate_args(name, kwargs)
        if val_error:
            logger.warning(f"Pre-validation failed for tool '{name}': {val_error}")
            return f"Validation Error: {val_error}"

        fn = self._tools[name]
        try:
            logger.info(f"Executing tool '{name}' with args: {kwargs}")
            result = fn(**kwargs)
            return result
        except Exception as e:
            err_msg = f"Error executing {name}: {type(e).__name__} - {str(e)}"
            logger.error(err_msg)
            return err_msg

