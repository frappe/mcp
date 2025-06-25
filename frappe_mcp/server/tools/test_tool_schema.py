from typing import Any

from frappe_mcp.server.tools.tool_schema import get_descriptions, get_input_schema

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
    assert get_input_schema(simple_function) == expected_schema


def test_function_with_optional():
    """Tests a function with optional types and default values."""

    def function_with_optional(a: int | None, b: str = "default") -> None:
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
    assert get_input_schema(function_with_optional) == expected_schema


def test_function_with_union():
    """Tests a function with Union types."""

    def function_with_union(a: int | str, b: float | bool | None) -> None:
        """A function with union types."""
        pass

    expected_schema = {
        "type": "object",
        "properties": {
            "a": {"anyOf": [{"type": "integer"}, {"type": "string"}]},
            "b": {"anyOf": [{"type": "number"}, {"type": "boolean"}, {"type": "null"}]},
        },
        "required": ["a", "b"],
    }
    assert get_input_schema(function_with_union) == expected_schema


def test_function_with_list():
    """Tests a function with list types."""

    def function_with_list(a: list, b: list[int]) -> None:
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
    assert get_input_schema(function_with_list) == expected_schema


def test_function_with_dict():
    """Tests a function with dict types."""

    def function_with_dict(a: dict, b: dict[str, int]) -> None:
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
    assert get_input_schema(function_with_dict) == expected_schema


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
    assert get_input_schema(function_with_any) == expected_schema


def test_function_no_params():
    """Tests a function with no parameters."""

    def function_no_params() -> None:
        """A function with no parameters."""
        pass

    assert get_input_schema(function_no_params) == {
        "type": "object",
        "properties": {},
    }


def test_function_with_forward_ref():
    """Tests a function with forward-referenced string type hints."""

    def function_with_forward_ref(a: "str", b: "int | None") -> None:
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
    assert get_input_schema(function_with_forward_ref) == expected_schema


def test_complex_function():
    """Tests a complex function with a mix of types."""

    def complex_function(
        a: int,
        b: str | None = None,
        c: list | dict = [1],  # noqa: B006
        d: list[int | str] = [],  # noqa: B006
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
    assert get_input_schema(complex_function) == expected_schema


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
    assert get_input_schema(function_with_pipe_union) == expected_schema


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
    assert get_input_schema(function_with_pipe_optional) == expected_schema


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
    assert get_input_schema(function_with_new_list_syntax) == expected_schema


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
    assert get_input_schema(function_with_new_dict_syntax) == expected_schema


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
    assert get_input_schema(function_with_new_complex_syntax) == expected_schema


# Test cases for get_descriptions function


def test_get_descriptions_empty_string():
    """Tests get_descriptions with an empty string."""
    description, args = get_descriptions("")
    assert description == ""
    assert args == {}


def test_get_descriptions_no_args():
    """Tests a docstring with only a description."""
    docstring = "This is a simple description."
    description, args = get_descriptions(docstring)
    assert description == "This is a simple description."
    assert args == {}


def test_get_descriptions_with_args():
    """Tests a standard docstring with an Args section."""
    docstring = """
    A function with a description.

    Args:
        param1: The first parameter.
        param2: The second parameter.
    """
    description, args = get_descriptions(docstring)
    assert description == "A function with a description."
    assert args == {
        "param1": "The first parameter.",
        "param2": "The second parameter.",
    }


def test_get_descriptions_with_types_in_args():
    """Tests a docstring where args have types."""
    docstring = """
    Another function.

    Args:
        param1 (str): The first parameter.
        param2 (int, optional): The second parameter.
    """
    description, args = get_descriptions(docstring)
    assert description == "Another function."
    assert args == {
        "param1": "The first parameter.",
        "param2": "The second parameter.",
    }


def test_get_descriptions_multiline_arg_description():
    """Tests an arg with a multiline description."""
    docstring = """
    A function.
    That has a multiline description.

    Args:
        param1: A parameter with a very long
            description that spans multiple
            lines.
    """
    description, args = get_descriptions(docstring)
    assert description == "A function.\nThat has a multiline description."
    assert args == {
        "param1": "A parameter with a very long description that spans multiple lines."
    }


def test_get_descriptions_no_description_part():
    """Tests a docstring that starts with Args."""
    docstring = """Args:
        param1: The first parameter."""
    description, args = get_descriptions(docstring)
    assert description == ""
    assert args == {"param1": "The first parameter."}
