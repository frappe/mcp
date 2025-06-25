from __future__ import annotations

from inspect import getdoc
from typing import Any, Callable, TypedDict

from frappe_mcp.server.tools.tool_schema import get_descriptions, get_input_schema

__all__ = ["Tool", "ToolOptions", "get_tool", "run_tool"]


class Tool(TypedDict):
    name: str
    description: str
    input_schema: dict[str, Any]
    fn: Callable


class ToolOptions(TypedDict):
    name: str | None
    description: str | None
    input_schema: dict | None
    use_entire_docstring: bool


def get_tool(fn: Callable, options: ToolOptions | None = None):
    if options is None:
        options = ToolOptions(
            name=None,
            description=None,
            input_schema=None,
            use_entire_docstring=False,
        )

    name = options.get("name") or fn.__name__
    description = options.get("description") or getdoc(fn) or ""
    input_schema = options.get("input_schema")

    _description, args = get_descriptions(description)
    if not options.get("use_entire_docstring") and description:
        description = _description

    _input_schema = get_input_schema(fn)
    for schema_key, schema_value in _input_schema.items():
        if schema_key not in args:
            continue
        schema_value["description"] = args[schema_key]
    input_schema = input_schema or _input_schema

    tool = Tool(
        name=name,
        description=description,
        input_schema=input_schema,
        fn=fn,
    )
    return tool


def run_tool(tool: Tool, arguments: dict[str, Any]):
    # tool.fn(**arguments)
    ...
