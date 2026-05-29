from __future__ import annotations

from collections import OrderedDict
from unittest.mock import MagicMock

import pytest

from frappe_mcp.server import types
from frappe_mcp.server.prompts import get_prompt
from frappe_mcp.server.prompts.handlers import handle_get_prompt, handle_list_prompts

# ---------------------------------------------------------------------------
# get_prompt
# ---------------------------------------------------------------------------


class TestGetPrompt:
    def test_name_from_function(self):
        def my_prompt():
            pass

        p = get_prompt(my_prompt)
        assert p['name'] == 'my_prompt'

    def test_description_from_docstring(self):
        def my_prompt():
            """Summarize something."""
            pass

        p = get_prompt(my_prompt)
        assert p['description'] == 'Summarize something.'

    def test_override_name_and_description(self):
        from frappe_mcp.server.prompts import PromptOptions

        def my_prompt():
            pass

        p = get_prompt(my_prompt, PromptOptions(name='custom', description='Custom desc'))
        assert p['name'] == 'custom'
        assert p['description'] == 'Custom desc'

    def test_arguments_inferred_from_signature(self):
        def my_prompt(topic: str, language: str = 'english'):
            pass

        p = get_prompt(my_prompt)
        assert p['arguments'] is not None
        args = {a['name']: a for a in p['arguments']}
        assert args['topic']['required'] is True
        assert args['language']['required'] is False

    def test_no_params_gives_none_arguments(self):
        def my_prompt():
            pass

        p = get_prompt(my_prompt)
        assert p['arguments'] is None

    def test_fn_stored(self):
        def fn():
            pass

        p = get_prompt(fn)
        assert p['fn'] is fn


# ---------------------------------------------------------------------------
# handle_list_prompts
# ---------------------------------------------------------------------------


class TestHandleListPrompts:
    def test_empty_registry(self):
        result = handle_list_prompts({}, OrderedDict())
        assert result == {'prompts': []}

    def test_lists_registered_prompts(self):
        registry = OrderedDict()
        registry['greet'] = {
            'name': 'greet',
            'description': 'Greet someone.',
            'arguments': [{'name': 'name', 'required': True}],
            'fn': MagicMock(),
        }
        result = handle_list_prompts({}, registry)
        assert len(result['prompts']) == 1
        p = result['prompts'][0]
        assert p['name'] == 'greet'
        assert p['description'] == 'Greet someone.'
        assert p['arguments'][0]['name'] == 'name'

    def test_prompt_without_arguments(self):
        registry = OrderedDict()
        registry['simple'] = {
            'name': 'simple',
            'description': None,
            'arguments': None,
            'fn': MagicMock(),
        }
        result = handle_list_prompts({}, registry)
        p = result['prompts'][0]
        assert 'arguments' not in p

    def test_multiple_prompts_order_preserved(self):
        registry = OrderedDict()
        for name in ['alpha', 'beta', 'gamma']:
            registry[name] = {'name': name, 'description': None, 'arguments': None, 'fn': MagicMock()}
        result = handle_list_prompts({}, registry)
        assert [p['name'] for p in result['prompts']] == ['alpha', 'beta', 'gamma']


# ---------------------------------------------------------------------------
# handle_get_prompt
# ---------------------------------------------------------------------------


class TestHandleGetPrompt:
    def _make_registry(self, name, fn, description=None, arguments=None):
        registry = OrderedDict()
        registry[name] = {'name': name, 'description': description, 'arguments': arguments, 'fn': fn}
        return registry

    def test_returns_messages_from_list(self):
        def my_prompt(topic: str):
            return [types.PromptMessage(role='user', content=types.TextContent(text=f'Tell me about {topic}'))]

        registry = self._make_registry('my_prompt', my_prompt)
        result = handle_get_prompt({'name': 'my_prompt', 'arguments': {'topic': 'Python'}}, registry)
        assert result['messages'][0]['content']['text'] == 'Tell me about Python'
        assert result['messages'][0]['role'] == 'user'

    def test_returns_get_prompt_result_directly(self):
        def my_prompt():
            return types.GetPromptResult(
                description='desc',
                messages=[types.PromptMessage(role='assistant', content=types.TextContent(text='Hi'))],
            )

        registry = self._make_registry('my_prompt', my_prompt)
        result = handle_get_prompt({'name': 'my_prompt'}, registry)
        assert result['messages'][0]['role'] == 'assistant'

    def test_unknown_prompt_raises(self):
        with pytest.raises(ValueError, match="not found"):
            handle_get_prompt({'name': 'missing'}, OrderedDict())

    def test_invalid_return_type_raises(self):
        def bad_prompt():
            return "just a string"

        registry = self._make_registry('bad', bad_prompt)
        with pytest.raises(ValueError, match="must return"):
            handle_get_prompt({'name': 'bad'}, registry)

    def test_no_arguments_param(self):
        def my_prompt():
            return [types.PromptMessage(role='user', content=types.TextContent(text='Hello'))]

        registry = self._make_registry('my_prompt', my_prompt)
        result = handle_get_prompt({'name': 'my_prompt'}, registry)
        assert len(result['messages']) == 1

    def test_description_in_result(self):
        def my_prompt():
            return [types.PromptMessage(role='user', content=types.TextContent(text='x'))]

        registry = self._make_registry('my_prompt', my_prompt, description='My desc')
        result = handle_get_prompt({'name': 'my_prompt'}, registry)
        assert result.get('description') == 'My desc'
