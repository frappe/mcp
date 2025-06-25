from __future__ import annotations

from collections.abc import Callable
from inspect import getdoc
from typing import Any, TypedDict

from jsonschema import validate

from frappe_mcp.server.tools.handlers import handle_call_tool, handle_list_tools
from frappe_mcp.server.tools.tool_schema import get_descriptions, get_input_schema

__all__ = [
    "Tool",
    "ToolAnnotations",
    "ToolOptions",
    "get_tool",
    "handle_call_tool",
    "handle_list_tools",
    "run_tool",
]


class Tool(TypedDict):
    name: str
    description: str
    input_schema: dict[str, Any]
    output_schema: dict[str, Any] | None
    annotations: ToolAnnotations | None
    fn: Callable


class ToolAnnotations(TypedDict, total=False):
    title: str | None
    readOnlyHint: bool | None
    destructiveHint: bool | None
    idempotentHint: bool | None
    openWorldHint: bool | None


class ToolOptions(TypedDict, total=False):
    name: str | None
    description: str | None
    input_schema: dict | None
    use_entire_docstring: bool
    annotations: ToolAnnotations | None


def get_tool(fn: Callable, options: ToolOptions | None = None):
    if options is None:
        options = ToolOptions(
            name=None,
            description=None,
            input_schema=None,
            use_entire_docstring=False,
            annotations=None,
        )

    name = options.get("name") or fn.__name__
    description = options.get("description") or getdoc(fn) or ""
    input_schema = options.get("input_schema")

    _description, args = get_descriptions(description)
    if not options.get("use_entire_docstring") and description:
        description = _description

    _input_schema = get_input_schema(fn)
    for schema_key, schema_value in _input_schema["properties"].items():
        if schema_key not in args:
            continue
        schema_value["description"] = args[schema_key]
    input_schema = input_schema or _input_schema

    tool = Tool(
        fn=fn,
        name=name,
        description=description,
        input_schema=input_schema,
        output_schema=None,
        annotations=options.get("annotations"),
    )
    return tool


def run_tool(tool: Tool, arguments: dict[str, Any]):
    validate(instance=arguments, schema=tool["input_schema"])
    properties = tool["input_schema"]["properties"]
    tool_args = {key: arguments[key] for key in arguments if key in properties}
    return tool["fn"](**tool_args)
