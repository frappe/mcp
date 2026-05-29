from __future__ import annotations

import inspect
from collections.abc import Callable
from inspect import getdoc
from typing import TypedDict

from frappe_mcp.server.prompts.handlers import handle_get_prompt, handle_list_prompts

__all__ = [
    'Prompt',
    'PromptArgument',
    'PromptOptions',
    'get_prompt',
    'handle_get_prompt',
    'handle_list_prompts',
]


class PromptArgument(TypedDict, total=False):
    name: str
    title: str | None
    description: str | None
    required: bool | None


class Prompt(TypedDict):
    name: str
    description: str | None
    arguments: list[PromptArgument] | None
    fn: Callable


class PromptOptions(TypedDict, total=False):
    name: str | None
    description: str | None
    arguments: list[PromptArgument] | None


def get_prompt(fn: Callable, options: PromptOptions | None = None) -> Prompt:
    if options is None:
        options = PromptOptions()

    name = options.get('name') or fn.__name__
    description = options.get('description') or getdoc(fn) or None
    arguments = options.get('arguments')

    if arguments is None:
        arguments = _get_arguments_from_fn(fn) or None

    return Prompt(fn=fn, name=name, description=description, arguments=arguments)


def _get_arguments_from_fn(fn: Callable) -> list[PromptArgument]:
    sig = inspect.signature(fn)
    args = []
    for param_name, param in sig.parameters.items():
        required = param.default is inspect.Parameter.empty
        args.append(PromptArgument(name=param_name, required=required))
    return args
