from __future__ import annotations

from collections import OrderedDict

from frappe_mcp.server import types


def handle_list_prompts(params, prompt_registry: OrderedDict) -> dict:
    types.ListPromptsRequestParams.model_validate(params)
    prompt_list = []
    for prompt_info in prompt_registry.values():
        raw_args = prompt_info.get('arguments') or []
        arguments = [
            types.PromptArgument(
                name=arg['name'],
                title=arg.get('title'),
                description=arg.get('description'),
                required=arg.get('required'),
            )
            for arg in raw_args
        ] or None
        prompt = types.Prompt(
            name=prompt_info['name'],
            description=prompt_info.get('description'),
            arguments=arguments,
        )
        prompt_list.append(prompt)
    result = types.ListPromptsResult(prompts=prompt_list)
    return result.model_dump(exclude_none=True, by_alias=True)


def handle_get_prompt(params, prompt_registry: OrderedDict) -> dict:
    get_params = types.GetPromptRequestParams.model_validate(params)
    name = get_params.name
    arguments = get_params.arguments or {}

    if name not in prompt_registry:
        raise ValueError(f"Prompt '{name}' not found.")

    prompt_info = prompt_registry[name]
    fn = prompt_info['fn']

    raw_result = fn(**arguments)

    if isinstance(raw_result, list):
        result = types.GetPromptResult(
            description=prompt_info.get('description'),
            messages=raw_result,
        )
    elif isinstance(raw_result, types.GetPromptResult):
        result = raw_result
    else:
        raise ValueError(
            f"Prompt '{name}' must return list[PromptMessage] or GetPromptResult, "
            f"got {type(raw_result).__name__}."
        )

    return result.model_dump(exclude_none=True, by_alias=True)
