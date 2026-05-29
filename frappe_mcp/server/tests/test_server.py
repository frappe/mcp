import io
import json

import pytest
from werkzeug.wrappers import Request, Response

from frappe_mcp.server import types
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


@pytest.fixture
def mcp_with_prompts():
    mcp = MCP(name='frappe-mcp')

    @mcp.prompt()
    def summarize(topic: str, language: str = 'english'):
        """Summarize a topic."""
        return [
            types.PromptMessage(
                role='user',
                content=types.TextContent(text=f'Summarize {topic} in {language}'),
            )
        ]

    @mcp.prompt()
    def no_args_prompt():
        """A prompt with no arguments."""
        return [types.PromptMessage(role='user', content=types.TextContent(text='Hello'))]

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


def _post(mcp, method, params=None, request_id=1):
    data = {'jsonrpc': '2.0', 'id': request_id, 'method': method, 'params': params or {}}
    request = Request.from_values(
        method='POST',
        content_type='application/json',
        input_stream=io.BytesIO(json.dumps(data).encode('utf-8')),
    )
    return json.loads(mcp.handle(request, Response()).data)


def test_initialize_has_prompts_capability(mcp_instance):
    result = _post(mcp_instance, 'initialize', {'clientInfo': {'name': 'test'}})
    assert 'prompts' in result['result']['capabilities']


def test_handle_list_prompts_empty(mcp_instance):
    result = _post(mcp_instance, 'prompts/list')
    assert result['result'] == {'prompts': []}


def test_handle_list_prompts(mcp_with_prompts):
    result = _post(mcp_with_prompts, 'prompts/list')
    prompts = result['result']['prompts']
    assert len(prompts) == 2
    names = {p['name'] for p in prompts}
    assert names == {'summarize', 'no_args_prompt'}


def test_handle_list_prompts_arguments(mcp_with_prompts):
    result = _post(mcp_with_prompts, 'prompts/list')
    summarize = next(p for p in result['result']['prompts'] if p['name'] == 'summarize')
    args = {a['name']: a for a in summarize['arguments']}
    assert args['topic']['required'] is True
    assert args['language']['required'] is False


def test_handle_get_prompt(mcp_with_prompts):
    result = _post(mcp_with_prompts, 'prompts/get', {'name': 'summarize', 'arguments': {'topic': 'Python'}})
    messages = result['result']['messages']
    assert len(messages) == 1
    assert messages[0]['role'] == 'user'
    assert 'Python' in messages[0]['content']['text']


def test_handle_get_prompt_default_arg(mcp_with_prompts):
    result = _post(mcp_with_prompts, 'prompts/get', {'name': 'summarize', 'arguments': {'topic': 'Go', 'language': 'french'}})
    assert 'french' in result['result']['messages'][0]['content']['text']


def test_handle_get_prompt_not_found(mcp_with_prompts):
    result = _post(mcp_with_prompts, 'prompts/get', {'name': 'nonexistent'})
    assert result.get('error') is not None
    assert result['error']['code'] == -32602


def test_unimplemented_method_returns_error(mcp_instance):
    result = _post(mcp_instance, 'completion/complete', {'ref': {}, 'argument': {}})
    assert result.get('error') is not None
    assert result['error']['code'] == -32601


def test_unknown_method_returns_error(mcp_instance):
    result = _post(mcp_instance, 'foo/bar')
    assert result.get('error') is not None
    assert result['error']['code'] == -32601


def test_handler_exception_returns_internal_error(mcp_instance):
    @mcp_instance.tool()
    def boom():
        """Raises unexpectedly."""
        raise RuntimeError('something went wrong')

    result = _post(mcp_instance, 'tools/call', {'name': 'boom', 'arguments': {}})
    assert result['result']['isError'] is True
