from __future__ import annotations


def handle_initialize(params, name: str):
    """
    Handles the initialize request from the client.
    """
    return {
        'protocolVersion': '2025-03-26',
        # "protocolVersion": "2024-11-05",
        'serverInfo': {'name': name, 'version': '0.1.0'},
        'capabilities': {
            'tools': {'listChanged': False},
            # Not yet implemented
            # "completions": {},
            # "prompts": {"listChanged": False},
            # "resources": {"subscribe": True, "listChanged": False},
            # "logging": {},
        },
    }


def handle_ping(_):
    """
    Handles the ping request from the client.
    https://modelcontextprotocol.io/specification/2025-03-26/basic/utilities/ping#ping
    """
    return {}


def handle_complete(params):
    raise NotImplementedError('handle_complete not implemented')


def handle_set_level(params):
    raise NotImplementedError('handle_set_level not implemented')


def handle_get_prompt(params):
    raise NotImplementedError('handle_get_prompt not implemented')


def handle_list_prompts(params):
    raise NotImplementedError('handle_list_prompts not implemented')


def handle_list_resources(params):
    raise NotImplementedError('handle_list_resources not implemented')


def handle_list_resource_templates(params):
    raise NotImplementedError('handle_list_resource_templates not implemented')


def handle_read_resource(params):
    raise NotImplementedError('handle_read_resource not implemented')


def handle_subscribe(params):
    raise NotImplementedError('handle_subscribe not implemented')


def handle_unsubscribe(params):
    raise NotImplementedError('handle_unsubscribe not implemented')


def handle_cancelled(params): ...
def handle_progress(params): ...
def handle_initialized(params): ...
def handle_roots_list_changed(params): ...
