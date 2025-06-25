from inspect import getdoc

import pytest
from jsonschema.exceptions import ValidationError

from frappe_mcp.server.tools import ToolOptions, get_tool, run_tool


def simple_tool_for_test(a: int, b: str = "default"):
    """This is a simple tool.

    Args:
        a: An integer.
        b: A string. Defaults to "default".

    Returns:
        Concatenation of a and b.
    """
    return f"{a}-{b}"


def another_simple_tool():
    """A tool with no arguments."""
    return "OK"


class TestGetTool:
    def test_get_tool_from_func(self):
        tool = get_tool(simple_tool_for_test)

        assert tool["name"] == "simple_tool_for_test"
        assert tool["description"] == "This is a simple tool."
        assert tool["fn"] == simple_tool_for_test

        assert "properties" in tool["input_schema"]
        properties = tool["input_schema"]["properties"]

        assert "a" in properties
        assert properties["a"]["type"] == "integer"
        assert properties["a"]["description"] == "An integer."

        assert "b" in properties
        assert properties["b"]["type"] == "string"
        # assert properties["b"]["default"] == "default"
        assert (
            properties["b"]["description"] == 'A string. Defaults to "default".'
        )

        assert tool["input_schema"]["required"] == ["a"]

    def test_get_tool_no_args(self):
        tool = get_tool(another_simple_tool)
        assert tool["name"] == "another_simple_tool"
        assert tool["description"] == "A tool with no arguments."
        assert tool["fn"] == another_simple_tool
        assert tool["input_schema"] == {
            "type": "object",
            "properties": {},
        }

    def test_get_tool_override_name(self):
        options = ToolOptions(name="my_cool_tool")
        tool = get_tool(simple_tool_for_test, options)
        assert tool["name"] == "my_cool_tool"
        assert tool["description"] == "This is a simple tool."

    def test_get_tool_override_description(self):
        options = ToolOptions(description="overridden description")
        tool = get_tool(simple_tool_for_test, options)
        assert tool["name"] == "simple_tool_for_test"
        assert tool["description"] == "overridden description"

    def test_get_tool_override_input_schema(self):
        custom_schema = {
            "type": "object",
            "properties": {"c": {"type": "boolean"}},
        }
        options = ToolOptions(input_schema=custom_schema)
        tool = get_tool(simple_tool_for_test, options)
        assert tool["input_schema"] == custom_schema

    def test_get_tool_use_entire_docstring(self):
        options = ToolOptions(use_entire_docstring=True)
        tool = get_tool(simple_tool_for_test, options)
        assert tool["description"] == getdoc(simple_tool_for_test)


class TestRunTool:
    def test_run_tool_success(self):
        tool = get_tool(simple_tool_for_test)
        result = run_tool(tool, {"a": 5, "b": "hello"})
        assert result == "5-hello"

    def test_run_tool_with_default_value(self):
        tool = get_tool(simple_tool_for_test)
        result = run_tool(tool, {"a": 5})
        assert result == "5-default"

    def test_run_tool_ignores_extra_args(self):
        tool = get_tool(simple_tool_for_test)
        result = run_tool(tool, {"a": 5, "c": "ignored"})
        assert result == "5-default"

    def test_run_tool_missing_required_arg(self):
        tool = get_tool(simple_tool_for_test)
        with pytest.raises(ValidationError):
            run_tool(tool, {"b": "hello"})

    def test_run_tool_wrong_arg_type(self):
        tool = get_tool(simple_tool_for_test)
        with pytest.raises(ValidationError):
            run_tool(tool, {"a": "not-an-int"})

    def test_run_tool_no_args(self):
        tool = get_tool(another_simple_tool)
        result = run_tool(tool, {})
        assert result == "OK"

    def test_run_tool_no_args_with_extra(self):
        tool = get_tool(another_simple_tool)
        result = run_tool(tool, {"a": 1})
        assert result == "OK" 