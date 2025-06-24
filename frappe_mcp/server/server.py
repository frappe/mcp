from werkzeug.wrappers import Request, Response
import frappe_mcp.server.handlers as handlers


def mcp_handler(request: Request, response: Response):
    if request.method != "POST":
        response.status_code = 405
        return

    try:
        data = request.get_json(force=True)
    except Exception:
        response.data = '{"jsonrpc": "2.0", "error": {"code": -32700, "message": "Parse error"}, "id": null}'
        response.mimetype = "application/json"
        response.status_code = 400
        return

    request_id = data.get("id")

    if "method" in data:
        if request_id is not None:
            # Request
            method = data["method"]
            params = data.get("params", {})

            # The type checks below are not exhaustive and are for demonstration
            # In a real implementation, you would have robust validation
            if not isinstance(method, str) or not isinstance(params, dict):
                response.data = (
                    '{"jsonrpc": "2.0", "error": {"code": -32602, "message": "Invalid params"}, "id": '
                    + str(request_id)
                    + "}"
                )
                response.mimetype = "application/json"
                response.status_code = 400
                return

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
                    error = {"code": -32601, "message": "Method not found"}

            if error:
                response.data = f'{{"jsonrpc": "2.0", "error": {{"code": {error["code"]}, "message": "{error["message"]}"}}, "id": {request_id}}}'
                response.mimetype = "application/json"
                response.status_code = 400
            else:
                response.data = f'{{"jsonrpc": "2.0", "result": {result if result is not None else "{}"}, "id": {request_id}}}'
                response.mimetype = "application/json"
                response.status_code = 200

        else:
            # Notification
            method = data["method"]
            params = data.get("params", {})

            if not isinstance(method, str) or not isinstance(params, dict):
                # Notifications with invalid params are ignored
                pass
            else:
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

    else:
        # Invalid Request
        response.data = f'{{"jsonrpc": "2.0", "error": {{"code": -32600, "message": "Invalid Request"}}, "id": {request_id if request_id is not None else "null"}}}'
        response.mimetype = "application/json"
        response.status_code = 400
