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
    """The main class for creating an MCP server.

    This class orchestrates the handling of JSON-RPC requests, manages a
    registry of available tools, and integrates with a web server framework
    to expose the MCP functionality.

    In a Frappe application, you would typically create a single instance of
    this class and use the `@mcp.register()` decorator on an API endpoint.
    Tools can be added using the `@mcp.tool()` decorator.

    Example:
        ```python
        # In app/mcp.py
        from frappe_mcp import MCP

        mcp = MCP(name="my-mcp-server")

        @mcp.tool()
        def my_tool(param1: str):
            '''A simple tool.'''
            return f"You said: {param1}"

        @mcp.register()
        def mcp_endpoint():
            '''The entry point for MCP requests.'''
            # This function body is executed before request handling.
            # It's a good place to import modules that register tools.
            pass
        ```

    For use in other Werkzeug-based servers, you can use the `mcp.handle()`
    method directly.
    """

    _name: str | None
    _tool_registry: OrderedDict[str, tools.Tool]
    _mcp_entry_fn: Callable | None

    def __init__(self, name: str | None):
        self._tool_registry = OrderedDict()
        self._name = name
        self._mcp_entry_fn = None

    def register(
        self,
        *,
        allow_guest: bool = False,
        xss_safe: bool = False,
    ):
        """A decorator to mark a function as an MCP endpoint.

        This is a wrapper around frappe.whitelist() that sets up the necessary
        configuration for handling MCP requests. The decorated function will be
        used as the entry point for all MCP requests.

        Only one function can be registered as an MCP endpoint per MCP instance.

        Args:
            allow_guest: If True, allows unauthenticated access to the endpoint.
            xss_safe: If True, response will not be sanitized for XSS.

        Raises:
            Exception: If not used in a Frappe app, or if already registered.
        """
        from werkzeug import Response

        try:
            import frappe
        except ImportError as e:
            raise Exception(
                'mcp.register can be used only in a Frappe app.\n'
                'If you are using it in some other Werkzeug based server\n'
                'you should use the mcp.handle function instead.'
            ) from e

        whitelister = frappe.whitelist(
            allow_guest=allow_guest,
            xss_safe=xss_safe,
            methods=['GET', 'POST'],
        )

        def decorator(fn):
            if self._mcp_entry_fn is not None:
                raise Exception('mcp.register can be used only once per MCP instance')

            self._mcp_entry_fn = fn

            def wrapper() -> Response:
                # Runs wrapped dummy mcp handler before handling the request.
                # This should import all the files with the registered mcp
                # functions.
                fn()

                request = frappe.request
                response = Response()

                return self.handle(request, response)

            return whitelister(wrapper)

        return decorator

    def handle(self, request: Request, response: Response) -> Response:
        """Handle an MCP request in any Werkzeug based server.

        This method can be used directly to integrate MCP functionality into any Werkzeug based server.
        It processes the request according to the MCP specification and returns an appropriate response.

        Args:
            request: The Werkzeug Request object containing the MCP request
            response: A Werkzeug Response object to be populated with the MCP response

        Returns:
            The populated Werkzeug Response object
        """
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
        name: str | None = None,
        description: str | None = None,
        input_schema: dict | None = None,
        use_entire_docstring: bool = False,
        annotations: tools.ToolAnnotations | None = None,
        # stream: bool = False,  # stream yes or no (SSE)
        # whitelist: list | None = None,
        # role: str | None = None,
    ):
        """A decorator that registers a function as a tool that can be used by an LLM.

        Example:
            >>> @mcp.tool()
            ... def get_current_weather(location: str, unit: str = "celsius"):
            ...     '''Get the current weather in a given location.'''
            ...     # ... implementation ...

        Args:
            name: The name of the tool. If not provided, the function's `__name__` will be used.
            description: A description of what the tool does. If not provided, it will be
                extracted from the function's docstring.
            input_schema: The JSON schema for the tool's input. If not provided, it will be
                inferred from the function's signature and docstring.
            use_entire_docstring: If True, the entire docstring will be used as the tool's
                description. Otherwise, only the first section is used (i.e. no Args).
            annotations: Additional context about the tool, such as validation information
                or examples of how to use it.
        """

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
            self.add_tool(tool)
            return fn

        return decorator

    def add_tool(self, tool: tools.Tool):
        """Registers a tool with the MCP instance.

        This method allows for adding a tool programmatically, serving as an
        alternative to the `@mcp.tool` decorator. The provided tool should
        be a dictionary conforming to the `frappe_mcp.Tool` `TypedDict` structure.

        Args:
            tool: The tool to register. It must be a dictionary with keys
                'name', 'description', 'input_schema', and 'fn'.
        """
        self._tool_registry[tool['name']] = tool

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
                result = handlers.handle_initialize(params, self._name or 'frappe-mcp')
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
                result = tools.handle_call_tool(params, self._tool_registry)
            case 'tools/list':
                result = tools.handle_list_tools(params, self._tool_registry)
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
