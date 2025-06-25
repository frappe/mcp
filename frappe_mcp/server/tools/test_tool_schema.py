from typing import Any, Dict, List, Optional, Union

from frappe_mcp.server.tools.tool_schema import get_schema

# Test cases for get_schema function


def test_simple_function():
    """Tests a simple function with basic type hints."""

    def simple_function(a: int, b: str) -> None:
        """A simple function with basic type hints."""
        pass

    expected_schema = {
        "type": "object",
        "properties": {
            "a": {"type": "integer"},
            "b": {"type": "string"},
        },
        "required": ["a", "b"],
    }
    assert get_schema(simple_function) == expected_schema


def test_function_with_optional():
    """Tests a function with optional types and default values."""

    def function_with_optional(a: Optional[int], b: str = "default") -> None:
        """A function with an optional type and a default value."""
        pass

    expected_schema = {
        "type": "object",
        "properties": {
            "a": {"type": ["integer", "null"]},
            "b": {"type": "string"},
        },
        "required": ["a"],
    }
    assert get_schema(function_with_optional) == expected_schema


def test_function_with_union():
    """Tests a function with Union types."""

    def function_with_union(a: Union[int, str], b: Union[float, bool, None]) -> None:
        """A function with union types."""
        pass

    expected_schema = {
        "type": "object",
        "properties": {
            "a": {"anyOf": [{"type": "integer"}, {"type": "string"}]},
            "b": {
                "anyOf": [{"type": "number"}, {"type": "boolean"}, {"type": "null"}]
            },
        },
        "required": ["a", "b"],
    }
    assert get_schema(function_with_union) == expected_schema


def test_function_with_list():
    """Tests a function with list types."""

    def function_with_list(a: list, b: List[int]) -> None:
        """A function with list types."""
        pass

    expected_schema = {
        "type": "object",
        "properties": {
            "a": {"type": "array"},
            "b": {"type": "array", "items": {"type": "integer"}},
        },
        "required": ["a", "b"],
    }
    assert get_schema(function_with_list) == expected_schema


def test_function_with_dict():
    """Tests a function with dict types."""

    def function_with_dict(a: dict, b: Dict[str, int]) -> None:
        """A function with dict types."""
        pass

    expected_schema = {
        "type": "object",
        "properties": {
            "a": {"type": "object"},
            "b": {"type": "object", "additionalProperties": {"type": "integer"}},
        },
        "required": ["a", "b"],
    }
    assert get_schema(function_with_dict) == expected_schema


def test_function_with_any():
    """Tests a function with Any type."""

    def function_with_any(a: Any) -> None:
        """A function with Any type."""
        pass

    expected_schema = {
        "type": "object",
        "properties": {"a": {}},
        "required": ["a"],
    }
    assert get_schema(function_with_any) == expected_schema


def test_function_no_params():
    """Tests a function with no parameters."""

    def function_no_params() -> None:
        """A function with no parameters."""
        pass

    assert get_schema(function_no_params) == {}


def test_function_with_forward_ref():
    """Tests a function with forward-referenced string type hints."""

    def function_with_forward_ref(a: "str", b: "Optional[int]") -> None:
        """A function with forward-referenced type hints."""
        pass

    expected_schema = {
        "type": "object",
        "properties": {
            "a": {"type": "string"},
            "b": {"type": ["integer", "null"]},
        },
        "required": ["a", "b"],
    }
    assert get_schema(function_with_forward_ref) == expected_schema


def test_complex_function():
    """Tests a complex function with a mix of types."""

    def complex_function(
        a: int,
        b: Optional[str] = None,
        c: Union[list, dict] = [1],
        d: List[Union[int, str]] = [],
    ) -> None:
        """A complex function with a mix of types."""
        pass

    expected_schema = {
        "type": "object",
        "properties": {
            "a": {"type": "integer"},
            "b": {"type": ["string", "null"]},
            "c": {"anyOf": [{"type": "array"}, {"type": "object"}]},
            "d": {
                "type": "array",
                "items": {"anyOf": [{"type": "integer"}, {"type": "string"}]},
            },
        },
        "required": ["a"],
    }
    assert get_schema(complex_function) == expected_schema


def test_function_with_pipe_union():
    """Tests a function with union type using pipe notation."""

    def function_with_pipe_union(a: int | str) -> None:
        """A function with union type using pipe notation."""
        pass

    expected_schema = {
        "type": "object",
        "properties": {
            "a": {"anyOf": [{"type": "integer"}, {"type": "string"}]},
        },
        "required": ["a"],
    }
    assert get_schema(function_with_pipe_union) == expected_schema


def test_function_with_pipe_optional():
    """Tests a function with optional type using pipe notation."""

    def function_with_pipe_optional(a: int | None) -> None:
        """A function with optional type using pipe notation."""
        pass

    expected_schema = {
        "type": "object",
        "properties": {
            "a": {"type": ["integer", "null"]},
        },
        "required": ["a"],
    }
    assert get_schema(function_with_pipe_optional) == expected_schema


def test_function_with_new_list_syntax():
    """Tests a function with new list syntax."""

    def function_with_new_list_syntax(a: list[int]) -> None:
        """A function with new list syntax."""
        pass

    expected_schema = {
        "type": "object",
        "properties": {
            "a": {"type": "array", "items": {"type": "integer"}},
        },
        "required": ["a"],
    }
    assert get_schema(function_with_new_list_syntax) == expected_schema


def test_function_with_new_dict_syntax():
    """Tests a function with new dict syntax."""

    def function_with_new_dict_syntax(a: dict[str, int]) -> None:
        """A function with new dict syntax."""
        pass

    expected_schema = {
        "type": "object",
        "properties": {
            "a": {"type": "object", "additionalProperties": {"type": "integer"}},
        },
        "required": ["a"],
    }
    assert get_schema(function_with_new_dict_syntax) == expected_schema


def test_function_with_new_complex_syntax():
    """Tests a function with new complex syntax."""

    def function_with_new_complex_syntax(a: list[int | str] | None) -> None:
        """A function with new complex syntax."""
        pass

    expected_schema = {
        "type": "object",
        "properties": {
            "a": {
                "type": ["array", "null"],
                "items": {"anyOf": [{"type": "integer"}, {"type": "string"}]},
            }
        },
        "required": ["a"],
    }
    assert get_schema(function_with_new_complex_syntax) == expected_schema
