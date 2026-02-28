from __future__ import annotations

from pydantic import ValidationError

from frappe_mcp.server import types


def handle_initialize(params, name: str):
    """
    Handles the initialize request from the client.
    """

    protocol_version = '2025-06-18'

    if isinstance(params, dict):
        requested_protocol = params.get('protocolVersion')
        if requested_protocol in {'2025-03-26', '2025-06-18'}:
            protocol_version = requested_protocol

    try:
        from frappe_mcp import __version__
    except Exception:  # pragma: no cover
        __version__ = '0.1.0'

    return {
        'protocolVersion': protocol_version,
        # "protocolVersion": "2024-11-05",
        'serverInfo': {'name': name, 'version': __version__},
        'capabilities': {
            'tools': {'listChanged': False},
            'prompts': {'listChanged': False},
            # Not yet implemented
            'completions': {},
            'resources': {'subscribe': True, 'listChanged': False},
            'logging': {},
        },
    }


def handle_ping(_):
    """
    Handles the ping request from the client.
    https://modelcontextprotocol.io/specification/2025-03-26/basic/utilities/ping#ping
    """
    return {}


def handle_complete(params):
    try:
        types.CompleteRequestParams.model_validate(params)
    except ValidationError:
        # For now, keep completion permissive to avoid blocking clients on
        # unsupported fields while this feature matures.
        pass

    return {'completion': {'values': []}}


def handle_set_level(params):
    types.SetLevelRequestParams.model_validate(params)
    return {}


def handle_get_prompt(params):
    types.GetPromptRequestParams.model_validate(params)
    return {'description': None, 'messages': []}


def handle_list_prompts(params):
    types.ListPromptsRequestParams.model_validate(params)
    return {'prompts': [], 'nextCursor': None}


def handle_list_resources(params):
    types.ListResourcesRequestParams.model_validate(params)
    return {'resources': [], 'nextCursor': None}


def handle_list_resource_templates(params):
    types.ListResourceTemplatesRequestParams.model_validate(params)
    return {'resourceTemplates': [], 'nextCursor': None}


def handle_read_resource(params):
    types.ReadResourceRequestParams.model_validate(params)
    return {'contents': []}


def handle_subscribe(params):
    types.SubscribeRequestParams.model_validate(params)
    return {}


def handle_unsubscribe(params):
    types.UnsubscribeRequestParams.model_validate(params)
    return {}


def handle_cancelled(params): ...
def handle_progress(params): ...
def handle_initialized(params): ...
def handle_roots_list_changed(params): ...
