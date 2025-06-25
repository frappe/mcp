from __future__ import annotations
from typing import Callable, Any, TypedDict


__all__ = ["Tool", "ToolOptions", "get_tool", "run_tool"]


class Tool(TypedDict):
    name: str
    description: str
    parameters: dict[str, Any]
    schema: dict[str, Any]
    fn: Callable


class ToolOptions(TypedDict):
    name: str | None
    description: str | None
    parameters: dict | None


def get_tool(fn: Callable, options: ToolOptions | None = None):
    if options is None:
        options = ToolOptions(name=None, description=None, parameters=None)

    name = options.get("name") or fn.__name__
    description = options.get("description") or fn.__doc__ or ""
    parameters = options.get("parameters") or fn.__annotations__

    if not parameters:
        ...

    schema = get_schema(name, description, parameters)
    tool = Tool(
        name=name,
        description=description,
        parameters=fn.__annotations__,
        schema={},
        fn=fn,
    )
    return tool


def run_tool(tool: Tool, arguments: dict[str, Any]):
    # tool.fn(**arguments)
    ...


def get_parameters():
    return {}


def get_schema(name: str, description: str, parameters: dict[str, Any]):
    return {}
