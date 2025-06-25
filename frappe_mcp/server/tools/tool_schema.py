import inspect
import re
import types
from collections.abc import Callable
from typing import (
    Any,
    Optional,
    Union,
    get_args,
    get_origin,
    get_type_hints,
)

# Mapping of Python types to JSON schema types
_PY_TO_JSON_TYPE_MAP = {
    int: 'integer',
    str: 'string',
    float: 'number',
    bool: 'boolean',
    type(None): 'null',
}


def _convert_py_to_json_type(py_type: Any) -> dict:
    """Convert a Python type to a JSON schema type dictionary."""
    if py_type in _PY_TO_JSON_TYPE_MAP:
        return {'type': _PY_TO_JSON_TYPE_MAP[py_type]}
    return {}


def _handle_union_type(py_type: Any) -> dict:
    """Handle Union and Optional types."""
    args = get_args(py_type)
    # Optional[T] is an alias for Union[T, None].
    is_optional = any(arg is type(None) for arg in args)

    # Filter out NoneType for processing
    non_none_args = [arg for arg in args if arg is not type(None)]

    if is_optional and len(non_none_args) == 1:
        # Handles Optional[T]
        schema = _convert_type_to_json_schema(non_none_args[0])
        # Add null type for optionality
        if 'type' in schema:
            if isinstance(schema['type'], list):
                if 'null' not in schema['type']:
                    schema['type'].append('null')
            else:
                schema['type'] = [schema['type'], 'null']
        else:
            # For complex types in Optional, wrap with anyOf
            return {'anyOf': [_convert_type_to_json_schema(arg) for arg in args]}
        return schema

    # Handles Union[T1, T2, ...]
    return {'anyOf': [_convert_type_to_json_schema(arg) for arg in args]}


def _handle_list_type(py_type: Any) -> dict:
    """Handle list types."""
    args = get_args(py_type)
    if args:
        # Handles list[T]
        return {'type': 'array', 'items': _convert_type_to_json_schema(args[0])}
    # Handles list
    return {'type': 'array'}


def _handle_dict_type(py_type: Any) -> dict:
    """Handle dict types."""
    args = get_args(py_type)
    if args and len(args) == 2:
        # Handles dict[K, V], assuming K is str
        return {
            'type': 'object',
            'additionalProperties': _convert_type_to_json_schema(args[1]),
        }
    # Handles dict
    return {'type': 'object'}


def _convert_type_to_json_schema(py_type: Any) -> dict:
    """Converts a Python type annotation to a JSON schema dictionary."""

    if py_type is list:
        return {'type': 'array'}
    if py_type is dict:
        return {'type': 'object'}

    # Handles simple types
    schema = _convert_py_to_json_type(py_type)
    if schema:
        return schema

    origin = get_origin(py_type)

    if origin in (Union, Optional, types.UnionType):
        # Handles Union and Optional types
        return _handle_union_type(py_type)

    if origin in (list, list):
        # Handles list types
        return _handle_list_type(py_type)

    if origin in (dict, dict):
        # Handles dict types
        return _handle_dict_type(py_type)

    if py_type is Any:
        # Handles Any type
        return {}

    # Fallback for unsupported types
    return {}


def get_input_schema(fn: Callable) -> dict:
    """
    Generate a JSON schema for a function's parameters.
    This function inspects the signature of `fn` and generates a JSON schema
    that describes the arguments, including their types and whether they are
    required.
    It supports standard Python types, as well as `Optional`, `Union`, `list`,
    and `dict` from the `typing` module.

    Example output:
    """
    try:
        # Resolve forward-referenced type hints
        type_hints = get_type_hints(fn)
    except (NameError, TypeError):
        # Fallback for unresolvable type hints
        type_hints = {}

    sig = inspect.signature(fn)
    parameters = sig.parameters
    input_schema = {
        'type': 'object',
        'properties': {},
    }

    if not parameters:
        return input_schema

    required_params = []

    for name, param in parameters.items():
        if param.kind not in (
            inspect.Parameter.POSITIONAL_OR_KEYWORD,
            inspect.Parameter.KEYWORD_ONLY,
        ):
            continue

        annotation = type_hints.get(name, Any)

        # Convert Python type to a JSON schema property
        prop_schema = _convert_type_to_json_schema(annotation)

        input_schema['properties'][name] = prop_schema

        # Determine if the parameter is required
        if param.default is inspect.Parameter.empty:
            required_params.append(name)

    if required_params:
        input_schema['required'] = required_params

    return input_schema


def get_descriptions(desc: str) -> tuple[str, dict[str, str]]:
    """
    Parses a Google-style docstring to extract the function description and
    parameter descriptions.

    Args:
        desc (str): The docstring to parse.

    Returns:
        A tuple containing:
            - str: The function's description.
            - dict: A dictionary of parameter descriptions, with parameter
              names as keys.
    """
    if not desc:
        return '', {}

    desc = inspect.cleandoc(desc)

    try:
        description_part, args_part = re.split(r'\n\s*Args:\n', desc, maxsplit=1)
    except ValueError:
        if desc.lstrip().startswith('Args:'):
            description_part = ''
            args_part = desc.lstrip()[len('Args:') :].lstrip()
        else:
            return desc, {}

    arg_pattern = re.compile(
        r'^\s*(\w+)\s*(?:\([^)]*\))?:\s*(.*?)(?=\n\s*\w+\s*(?:\(.*\))?:|\Z)',
        re.MULTILINE | re.DOTALL,
    )
    arg_descriptions = {}
    for match in arg_pattern.finditer(args_part):
        arg_name, description = match.groups()
        arg_descriptions[arg_name] = ' '.join(description.strip().split())

    return description_part.strip(), arg_descriptions
