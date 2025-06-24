from __future__ import annotations

import json

from pydantic import BaseModel, ValidationError
from werkzeug.wrappers import Request, Response

import frappe_mcp.server.handlers as handlers
from frappe_mcp.server import types, RequestId

__all__ = ["mcp_handler"]


def mcp_handler(request: Request, response: Response) -> Response:
    if request.method != "POST":
        response.status_code = 405
        return response

    try:
        data = request.get_json(force=True)
    except json.JSONDecodeError:
        return handle_invalid(None, response, types.PARSE_ERROR, "Parse error")

    if (request_id := data.get("id")) is None:
        return handle_invalid(
            request_id, response, types.INVALID_REQUEST, "Invalid Request"
        )

    if "method" in data:
        return handle_request(request_id, data, response)
    else:
        return handle_notification(data, response)


def handle_request(request_id: RequestId, data: dict, response: Response) -> Response:
    # Request
    try:
        rpc_request = types.JSONRPCRequest.model_validate(data)
    except ValidationError as e:
        return handle_invalid(
            request_id,
            response,
            types.INVALID_PARAMS,
            f"Invalid params: {e}",
        )

    method = rpc_request.method
    params = rpc_request.params or {}

    result = None
    error = None

    match method:
        case "initialize":
            result = handlers.handle_initialize(params)
        case "ping":
            result = handlers.handle_ping(params)
        case "completion/complete":
            result = handlers.handle_complete(params)
        case "logging/setLevel":
            result = handlers.handle_set_level(params)
        case "prompts/get":
            result = handlers.handle_get_prompt(params)
        case "prompts/list":
            result = handlers.handle_list_prompts(params)
        case "resources/list":
            result = handlers.handle_list_resources(params)
        case "resources/templates/list":
            result = handlers.handle_list_resource_templates(params)
        case "resources/read":
            result = handlers.handle_read_resource(params)
        case "resources/subscribe":
            result = handlers.handle_subscribe(params)
        case "resources/unsubscribe":
            result = handlers.handle_unsubscribe(params)
        case "tools/call":
            result = handlers.handle_call_tool(params)
        case "tools/list":
            result = handlers.handle_list_tools(params)
        case _:
            error = {"code": types.METHOD_NOT_FOUND, "message": "Method not found"}

    if error:
        return handle_invalid(request_id, response, error["code"], error["message"])

    success_response = types.JSONRPCSuccessResponse(
        id=request_id, result=result if result is not None else {}
    )
    response.data = get_response_data(success_response)
    response.mimetype = "application/json"
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
            case "notifications/cancelled":
                handlers.handle_cancelled(params)
            case "notifications/progress":
                handlers.handle_progress(params)
            case "notifications/initialized":
                handlers.handle_initialized(params)
            case "notifications/roots/list_changed":
                handlers.handle_roots_list_changed(params)

    response.status_code = 204
    return response


def handle_invalid(
    request_id: RequestId, response: Response, code: int, message: str
) -> Response:
    error_response = types.JSONRPCErrorResponse(
        id=request_id if request_id is not None else None,
        error=types.Error(code=code, message=message),
    )
    response.data = get_response_data(error_response)
    response.mimetype = "application/json"
    response.status_code = 400
    return response


def get_response_data(model: BaseModel):
    return model.model_dump_json(exclude_none=True, by_alias=True)
