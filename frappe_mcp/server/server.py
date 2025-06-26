from __future__ import annotations

import json
from collections import OrderedDict
from collections.abc import Callable

from pydantic import BaseModel, ValidationError
from werkzeug.wrappers import Request, Response

import frappe_mcp.server.handlers as handlers
import frappe_mcp.server.tools as tools
from frappe_mcp.server import types

__all__ = ['MCP']


class MCP:
    tool_registry: OrderedDict[str, tools.Tool]
    mcp_entry_fn: Callable | None

    def __init__(self):
        self.tool_registry = OrderedDict()

    def handler(self, allow_guest: bool = False):
        from werkzeug import Response

        try:
            import frappe
        except ImportError as e:
            raise Exception(
                'mcp.handler can be used only in a Frappe app.\n'
                'If you are using it in some other Werkzeug based server\n'
                'you should use the mcp.handle function instead.'
            ) from e

        whitelister = frappe.whitelist(
            allow_guest=allow_guest,
            xss_safe=False,
            methods=['GET', 'POST'],
        )

        def decorator(fn):
            fn_whitelisted = whitelister(fn)
            self.mcp_entry_fn = fn

            def wrapper(*args, **kwargs):
                # Runs wrapped dummy mcp handler before handling the request.
                # This should import all the files with the registered mcp
                # functions.
                fn_whitelisted(*args, **kwargs)

                request = frappe.request
                response = Response()

                return self.handle(request, response)

            return wrapper

        return decorator

    def handle(self, request: Request, response: Response) -> Response:
        if request.method != 'POST':
            response.status_code = 405
            return response

        try:
            data = request.get_json(force=True)
        except json.JSONDecodeError:
            return handle_invalid(None, response, types.PARSE_ERROR, 'Parse error')

        if get_is_notification(data):
            return handle_notification(data, response)

        if (request_id := data.get('id')) is None:
            return handle_invalid(
                request_id,
                response,
                types.INVALID_REQUEST,
                'Invalid Request',
            )

        return self._handle_request(request_id, data, response)

    def tool(
        self,
        *,
        # use this as tool name instead of the __name__ property of the function
        name: str | None = None,
        # use this as tool description instead of extracting it from __doc__
        description: str | None = None,
        # use this as tool's JSON schema instead of extracting from function signature and docstring
        input_schema: dict | None = None,
        # passes entire docstring as description instead of extracting it from docstring
        use_entire_docstring: bool = False,
        # use this to pass additional context about the tool
        # https://modelcontextprotocol.io/docs/concepts/tools#tool-annotations
        annotations: tools.ToolAnnotations | None = None,
        # stream: bool = False,  # stream yes or no (SSE)
        # whitelist: list | None = None,
        # role: str | None = None,
    ):
        def decorator(fn: Callable):
            tool = tools.get_tool(
                fn,
                tools.ToolOptions(
                    name=name,
                    description=description,
                    input_schema=input_schema,
                    use_entire_docstring=use_entire_docstring,
                    annotations=annotations,
                ),
            )
            self.tool_registry[tool['name']] = tool
            return fn

        return decorator

    def _handle_request(
        self,
        request_id: types.RequestId,
        data: dict,
        response: Response,
    ) -> Response:
        # Request
        try:
            rpc_request = types.JSONRPCRequest.model_validate(data)
        except ValidationError as e:
            return handle_invalid(
                request_id,
                response,
                types.INVALID_PARAMS,
                f'Invalid params: {e}',
            )

        method = rpc_request.method
        params = rpc_request.params or {}

        result = None

        match method:
            case 'initialize':
                result = handlers.handle_initialize(params)
            case 'ping':
                result = handlers.handle_ping(params)
            case 'completion/complete':
                result = handlers.handle_complete(params)
            case 'logging/setLevel':
                result = handlers.handle_set_level(params)
            case 'prompts/get':
                result = handlers.handle_get_prompt(params)
            case 'prompts/list':
                result = handlers.handle_list_prompts(params)
            case 'resources/list':
                result = handlers.handle_list_resources(params)
            case 'resources/templates/list':
                result = handlers.handle_list_resource_templates(params)
            case 'resources/read':
                result = handlers.handle_read_resource(params)
            case 'resources/subscribe':
                result = handlers.handle_subscribe(params)
            case 'resources/unsubscribe':
                result = handlers.handle_unsubscribe(params)
            case 'tools/call':
                result = tools.handle_call_tool(params, self.tool_registry)
            case 'tools/list':
                result = tools.handle_list_tools(params, self.tool_registry)
            case _:
                return handle_invalid(
                    request_id,
                    response,
                    types.METHOD_NOT_FOUND,
                    'Method not found',
                )

        result = {} if result is None else result
        success_response = types.JSONRPCSuccessResponse(id=request_id, result=result)
        response.data = get_response_data(success_response)
        response.mimetype = 'application/json'
        response.status_code = 200
        return response


def handle_notification(data: dict, response: Response) -> Response:
    # Notification
    try:
        rpc_notification = types.JSONRPCNotification.model_validate(data)
    except ValidationError:
        # Notifications with invalid params are ignored
        pass
    else:
        method = rpc_notification.method
        params = rpc_notification.params or {}
        match method:
            case 'notifications/cancelled':
                handlers.handle_cancelled(params)
            case 'notifications/progress':
                handlers.handle_progress(params)
            case 'notifications/initialized':
                handlers.handle_initialized(params)
            case 'notifications/roots/list_changed':
                handlers.handle_roots_list_changed(params)

    response.status_code = 202  # Accepted
    return response


def handle_invalid(
    request_id: types.RequestId,
    response: Response,
    code: int,
    message: str,
) -> Response:
    error_response = types.JSONRPCErrorResponse(
        id=request_id if request_id is not None else None,
        error=types.Error(code=code, message=message),
    )
    response.data = get_response_data(error_response)
    response.mimetype = 'application/json'
    response.status_code = 400
    return response


def get_response_data(model: BaseModel):
    return model.model_dump_json(exclude_none=True, by_alias=True)


def get_is_notification(data: dict) -> bool:
    method = data.get('method', '')
    return isinstance(method, str) and method.startswith('notifications/')
