import io
import json

import pytest
from werkzeug.wrappers import Request, Response

from frappe_mcp.server.server import MCP


@pytest.fixture
def mcp_instance():
    mcp = MCP(name='frappe-mcp')

    @mcp.tool()
    def adder(a: int, b: int) -> dict:
        """Adds two numbers."""
        return {'output': a + b}

    @mcp.tool()
    def subtractor(a: int, b: int):
        """Subtracts two numbers."""
        return a - b

    return mcp


def test_handle_initialize(mcp_instance):
    request_data = {
        'jsonrpc': '2.0',
        'id': 1,
        'method': 'initialize',
        'params': {'clientInfo': {'name': 'test-client'}},
    }
    request = Request.from_values(
        method='POST',
        content_type='application/json',
        input_stream=io.BytesIO(json.dumps(request_data).encode('utf-8')),
    )

    response = mcp_instance.handle(request, Response())

    assert response.status_code == 200
    response_data = json.loads(response.data)
    assert response_data['id'] == 1
    assert 'result' in response_data
    assert 'serverInfo' in response_data['result']
    assert response_data['result']['serverInfo']['name'] == 'frappe-mcp'


def test_handle_initialized_notification(mcp_instance):
    request_data = {
        'jsonrpc': '2.0',
        'method': 'notifications/initialized',
        'params': {},
    }
    request = Request.from_values(
        method='POST',
        content_type='application/json',
        input_stream=io.BytesIO(json.dumps(request_data).encode('utf-8')),
    )

    response = mcp_instance.handle(request, Response())

    assert response.status_code == 202
    assert not response.data


def test_handle_list_tools(mcp_instance):
    request_data = {'jsonrpc': '2.0', 'id': 2, 'method': 'tools/list', 'params': {}}
    request = Request.from_values(
        method='POST',
        content_type='application/json',
        input_stream=io.BytesIO(json.dumps(request_data).encode('utf-8')),
    )

    response = mcp_instance.handle(request, Response())

    assert response.status_code == 200
    response_data = json.loads(response.data)
    assert response_data['id'] == 2
    assert 'result' in response_data
    assert 'tools' in response_data['result']
    tools = response_data['result']['tools']
    assert len(tools) == 2
    tool_names = {tool['name'] for tool in tools}
    assert tool_names == {'adder', 'subtractor'}


def test_handle_call_tool_with_structured_content(mcp_instance):
    request_data = {
        'jsonrpc': '2.0',
        'id': 3,
        'method': 'tools/call',
        'params': {'name': 'adder', 'arguments': {'a': 5, 'b': 10}},
    }
    request = Request.from_values(
        method='POST',
        content_type='application/json',
        input_stream=io.BytesIO(json.dumps(request_data).encode('utf-8')),
    )

    response = mcp_instance.handle(request, Response())

    assert response.status_code == 200
    response_data = json.loads(response.data)
    assert response_data['id'] == 3
    assert 'result' in response_data
    assert response_data['result']['structuredContent'] == {'output': 15}


def test_handle_call_tool_with_regular_content(mcp_instance):
    request_data = {
        'jsonrpc': '2.0',
        'id': 3,
        'method': 'tools/call',
        'params': {'name': 'subtractor', 'arguments': {'a': 7, 'b': 4}},
    }
    request = Request.from_values(
        method='POST',
        content_type='application/json',
        input_stream=io.BytesIO(json.dumps(request_data).encode('utf-8')),
    )

    response = mcp_instance.handle(request, Response())

    assert response.status_code == 200
    response_data = json.loads(response.data)
    assert response_data['id'] == 3
    assert 'result' in response_data
    # assert response_data['result']['structuredContent'] is None
    assert response_data['result']['content'] == [{'type': 'text', 'text': '3'}]


def test_handle_initialize_has_full_capabilities(mcp_instance):
    request_data = {
        'jsonrpc': '2.0',
        'id': 4,
        'method': 'initialize',
        'params': {
            'protocolVersion': '2025-06-18',
            'clientInfo': {'name': 'test-client'},
            'capabilities': {},
        },
    }
    request = Request.from_values(
        method='POST',
        content_type='application/json',
        input_stream=io.BytesIO(json.dumps(request_data).encode('utf-8')),
    )

    response = mcp_instance.handle(request, Response())

    assert response.status_code == 200
    response_data = json.loads(response.data)
    capabilities = response_data['result']['capabilities']
    assert 'tools' in capabilities
    assert 'prompts' in capabilities
    assert 'resources' in capabilities
    assert 'logging' in capabilities
    assert 'completions' in capabilities


def _make_request(method: str, method_id: int = 10, params: dict | None = None):
    return Request.from_values(
        method='POST',
        content_type='application/json',
        input_stream=io.BytesIO(
            json.dumps(
                {
                    'jsonrpc': '2.0',
                    'id': method_id,
                    'method': method,
                    'params': params or {},
                }
            ).encode('utf-8')
        ),
    )


def test_handle_empty_compatibility_methods(mcp_instance):
    cases = [
        ('ping', {}),
        ('completion/complete', {'ref': {'type': 'ref/prompt'}}),
        ('logging/setLevel', {'level': 'debug'}),
        ('prompts/list', {}),
        ('resources/list', {}),
        ('resources/templates/list', {}),
        ('prompts/get', {'name': 'does-not-exist'}),
        ('resources/read', {'uri': 'file:///tmp'}),
        ('resources/subscribe', {'uri': 'file:///tmp'}),
        ('resources/unsubscribe', {'uri': 'file:///tmp'}),
    ]

    for i, (method, params) in enumerate(cases, start=20):
        request = _make_request(method, i, params)
        response = mcp_instance.handle(request, Response())
        assert response.status_code == 200

        response_data = json.loads(response.data)
        assert response_data['id'] == i
        assert 'result' in response_data
