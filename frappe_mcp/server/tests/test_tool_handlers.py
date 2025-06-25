from __future__ import annotations

import unittest
from typing import cast
from unittest.mock import MagicMock

from frappe_mcp.server import types
from frappe_mcp.server.tools import Tool as ServerTool
from frappe_mcp.server.tools import handlers as tool_handlers


class TestToolHandlers(unittest.TestCase):
    def test_get_validated_tool_success(self):
        """
        Test that a valid tool is correctly converted.
        """
        mock_fn = MagicMock()
        tool: ServerTool = {
            "name": "test_tool",
            "description": "A test tool",
            "input_schema": {
                "type": "object",
                "properties": {
                    "a": {"type": "string", "description": "A test property"}
                },
            },
            "output_schema": {"type": "object", "properties": {}},
            "annotations": {"title": "Test Tool"},
            "fn": mock_fn,
        }

        validated_tool = tool_handlers.get_validated_tool(tool)
        self.assertIsNotNone(validated_tool)
        self.assertIsInstance(validated_tool, types.Tool)
        assert validated_tool is not None
        self.assertEqual(validated_tool.name, "test_tool")
        self.assertEqual(validated_tool.description, "A test tool")
        self.assertIsNotNone(validated_tool.outputSchema)
        self.assertIsNotNone(validated_tool.annotations)

    def test_get_validated_tool_optional_fields(self):
        """
        Test that a tool with optional fields missing is correctly converted.
        """
        mock_fn = MagicMock()
        tool: ServerTool = {
            "name": "test_tool_no_optionals",
            "description": "A test tool without optional fields",
            "input_schema": {"type": "object", "properties": {}},
            "output_schema": None,
            "annotations": None,
            "fn": mock_fn,
        }

        validated_tool = tool_handlers.get_validated_tool(tool)
        self.assertIsNotNone(validated_tool)
        self.assertIsInstance(validated_tool, types.Tool)
        assert validated_tool is not None
        self.assertEqual(validated_tool.name, "test_tool_no_optionals")
        self.assertIsNone(validated_tool.outputSchema)
        self.assertIsNone(validated_tool.annotations)

    def test_get_validated_tool_invalid(self):
        """
        Test that an invalid tool returns None.
        """
        # Missing 'name' which is required
        tool = {
            "description": "An invalid test tool",
            "input_schema": {"type": "object", "properties": {}},
            "fn": MagicMock(),
        }

        # The function expects a ServerTool, so we need to cast it to Any to bypass static analysis
        validated_tool = tool_handlers.get_validated_tool(cast(ServerTool, tool))
        self.assertIsNone(validated_tool)
