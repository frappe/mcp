"""Tests for the DocType fieldtype -> JSON Schema helper.

These tests use plain dict fixtures shaped like Frappe `DocField` objects.
They exercise `frappe_fieldtype_to_json_schema` in isolation — no bench, no
site, no database. That's deliberate: the helper is a pure function of its
input, and the DocType-integration tests live in test_tools.py once the
`expose_doctype` wiring lands.
"""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from frappe_mcp.server.tools import doctype as doctype_module
from frappe_mcp.server.tools.doctype import build_tool, frappe_fieldtype_to_json_schema


def _fake_frappe(*, permission: bool = True, doc: dict | None = None, list_result=None, list_calls=None):
    """Minimal frappe stand-in for handler tests."""
    doc = doc if doc is not None else {"name": "x", "doctype": "ToDo"}
    list_result = list_result if list_result is not None else []

    def get_list(dt, **kwargs):
        if list_calls is not None:
            list_calls.append({"doctype": dt, **kwargs})
        return list_result

    return SimpleNamespace(
        has_permission=lambda *a, **k: permission,
        get_doc=lambda dt, name: SimpleNamespace(as_dict=lambda: {**doc, "name": name, "doctype": dt}),
        db=SimpleNamespace(get_list=get_list),
    )


# A minimal DocField shape. Real DocFields have ~40 keys; the helper only
# reads these four, and the test proves that boundary.
def _field(fieldtype: str, **overrides) -> dict:
    # Deliberately no default `fieldname` / `label`: tests that don't set them
    # expect the schema to omit `description`.
    base = {"fieldtype": fieldtype, "label": "", "fieldname": "", "options": ""}
    base.update(overrides)
    return base


class TestTextFieldtypes:
    """Text-shaped fieldtypes and unknown fieldtypes both fall through to string."""

    @pytest.mark.parametrize(
        "fieldtype",
        [
            "Data", "Small Text", "Long Text", "Text",
            "Text Editor", "Markdown Editor", "HTML Editor",
            "Code", "JSON", "Password", "Read Only",
            "Autocomplete", "Attach", "Attach Image", "Signature",
            "Color", "Geolocation", "Barcode", "Duration",
            "Phone", "Icon",  # Frappe adds these to data_fieldtypes; still strings.
            "SomeFutureFieldtypeFrappeMightAdd",  # unknown -> permissive default.
        ],
    )
    def test_maps_to_string(self, fieldtype):
        assert frappe_fieldtype_to_json_schema(_field(fieldtype))["type"] == "string"


class TestNumericFieldtypes:
    @pytest.mark.parametrize("fieldtype", ["Int", "Long Int"])
    def test_integer_types(self, fieldtype):
        assert frappe_fieldtype_to_json_schema(_field(fieldtype)) == {"type": "integer"}

    @pytest.mark.parametrize("fieldtype", ["Float", "Currency", "Percent", "Rating"])
    def test_number_types(self, fieldtype):
        # Rating is deliberately here: Frappe classifies it outside
        # numeric_fieldtypes, but semantically it is a number.
        assert frappe_fieldtype_to_json_schema(_field(fieldtype)) == {"type": "number"}


class TestCheckIsBoolean:
    def test_check_maps_to_boolean_not_integer(self):
        # Frappe stores Check as 0/1 (it's in numeric_fieldtypes), but a
        # JSON boolean is what an LLM should generate. Regression guard.
        assert frappe_fieldtype_to_json_schema(_field("Check")) == {"type": "boolean"}


class TestDateTimeFieldtypes:
    @pytest.mark.parametrize(
        "fieldtype, expected_format",
        [("Date", "date"), ("Datetime", "date-time"), ("Time", "time")],
    )
    def test_datetime_types(self, fieldtype, expected_format):
        schema = frappe_fieldtype_to_json_schema(_field(fieldtype))
        assert schema["type"] == "string"
        assert schema["format"] == expected_format


class TestSelectFieldtype:
    def test_options_become_enum(self):
        field = _field("Select", options="Open\nClosed\nCancelled", label="Status")
        assert frappe_fieldtype_to_json_schema(field) == {
            "type": "string",
            "enum": ["Open", "Closed", "Cancelled"],
            "description": "Status",
        }

    def test_blank_lines_and_whitespace_are_stripped(self):
        field = _field("Select", options="\n  Open  \n\nClosed\n  \n")
        assert frappe_fieldtype_to_json_schema(field)["enum"] == ["Open", "Closed"]

    def test_no_options_omits_enum(self):
        # Select fields without options are unusual but must not blow up.
        schema = frappe_fieldtype_to_json_schema(_field("Select", options=""))
        assert schema == {"type": "string"}


class TestLinkFieldtypes:
    @pytest.mark.parametrize("fieldtype", ["Link", "Dynamic Link"])
    def test_target_doctype_becomes_hint(self, fieldtype):
        field = _field(fieldtype, options="User", label="Assigned To")
        schema = frappe_fieldtype_to_json_schema(field)
        # The x-frappe-* extension is what MCP clients / LLMs use to know
        # "pass the primary key of a User here" rather than any string.
        assert schema == {
            "type": "string",
            "x-frappe-link-doctype": "User",
            "description": "Assigned To",
        }

    def test_link_without_target_still_returns_string(self):
        schema = frappe_fieldtype_to_json_schema(_field("Link", options=""))
        assert schema == {"type": "string"}
        assert "x-frappe-link-doctype" not in schema


class TestLabelBecomesDescription:
    def test_label_is_used_as_description(self):
        schema = frappe_fieldtype_to_json_schema(_field("Data", label="Full Name"))
        assert schema["description"] == "Full Name"

    def test_fieldname_used_when_label_missing(self):
        schema = frappe_fieldtype_to_json_schema(_field("Data", label="", fieldname="full_name"))
        assert schema["description"] == "full_name"

    def test_no_description_when_both_missing(self):
        schema = frappe_fieldtype_to_json_schema({"fieldtype": "Data"})
        assert "description" not in schema


class TestDefaults:
    def test_missing_fieldtype_treated_as_data(self):
        # DocFields nearly always have fieldtype, but defensive: if it's
        # missing/None the caller should still get a callable schema.
        assert frappe_fieldtype_to_json_schema({})["type"] == "string"


class TestBuildToolDispatch:
    def test_unknown_operation_raises(self):
        with pytest.raises(ValueError, match="Unsupported operation"):
            build_tool("ToDo", "explode")


class TestGetOperation:
    @pytest.mark.parametrize(
        "doctype, expected_name",
        [("ToDo", "get_todo"), ("Sales Invoice", "get_sales_invoice"), ("User", "get_user")],
    )
    def test_tool_name_is_snake_cased(self, doctype, expected_name):
        assert build_tool(doctype, "get")["name"] == expected_name

    def test_input_schema_requires_string_name(self):
        schema = build_tool("ToDo", "get")["input_schema"]
        assert schema["type"] == "object"
        assert schema["required"] == ["name"]
        assert schema["properties"]["name"]["type"] == "string"

    def test_marked_read_only(self):
        # Signals to MCP clients / LLMs that the tool is safe to call speculatively.
        assert build_tool("ToDo", "get")["annotations"]["readOnlyHint"] is True

    def test_handler_returns_document_as_dict(self, monkeypatch):
        monkeypatch.setattr(doctype_module, "_frappe", lambda: _fake_frappe())
        result = build_tool("ToDo", "get")["fn"](name="task-1")
        assert result["doctype"] == "ToDo"
        assert result["name"] == "task-1"

    def test_handler_raises_when_permission_denied(self, monkeypatch):
        monkeypatch.setattr(doctype_module, "_frappe", lambda: _fake_frappe(permission=False))
        with pytest.raises(PermissionError):
            build_tool("ToDo", "get")["fn"](name="task-1")

    def test_check_permissions_false_skips_the_check(self, monkeypatch):
        calls = []

        def has_permission(*a, **k):
            calls.append((a, k))
            return False

        fake = SimpleNamespace(
            has_permission=has_permission,
            get_doc=lambda dt, name: SimpleNamespace(as_dict=lambda: {"name": name}),
        )
        monkeypatch.setattr(doctype_module, "_frappe", lambda: fake)

        build_tool("ToDo", "get", check_permissions=False)["fn"](name="task-1")

        assert calls == []


class TestListOperation:
    @pytest.mark.parametrize(
        "doctype, expected_name",
        [("ToDo", "list_todo"), ("Sales Invoice", "list_sales_invoice")],
    )
    def test_tool_name_is_snake_cased(self, doctype, expected_name):
        assert build_tool(doctype, "list")["name"] == expected_name

    def test_input_schema_has_no_required_args(self):
        schema = build_tool("ToDo", "list")["input_schema"]
        assert schema["type"] == "object"
        assert "required" not in schema  # everything is optional
        assert set(schema["properties"]) == {"filters", "fields", "limit", "offset", "order_by"}

    def test_marked_read_only(self):
        assert build_tool("ToDo", "list")["annotations"]["readOnlyHint"] is True

    def test_handler_defaults_are_applied(self, monkeypatch):
        calls = []
        monkeypatch.setattr(
            doctype_module, "_frappe", lambda: _fake_frappe(list_calls=calls, list_result=[])
        )

        build_tool("ToDo", "list")["fn"]()

        assert calls == [{
            "doctype": "ToDo",
            "filters": {},
            "fields": ["name"],
            "limit": 20,
            "start": 0,
            "order_by": None,
        }]

    def test_handler_passes_arguments_through(self, monkeypatch):
        calls = []
        monkeypatch.setattr(
            doctype_module, "_frappe", lambda: _fake_frappe(list_calls=calls, list_result=[])
        )

        build_tool("ToDo", "list")["fn"](
            filters={"status": "Open"},
            fields=["name", "description"],
            limit=5,
            offset=10,
            order_by="modified desc",
        )

        assert calls[0]["filters"] == {"status": "Open"}
        assert calls[0]["fields"] == ["name", "description"]
        assert calls[0]["limit"] == 5
        assert calls[0]["start"] == 10          # note: Frappe's API param is `start`, not `offset`
        assert calls[0]["order_by"] == "modified desc"

    def test_handler_returns_frappe_list_verbatim(self, monkeypatch):
        rows = [{"name": "task-1"}, {"name": "task-2"}]
        monkeypatch.setattr(doctype_module, "_frappe", lambda: _fake_frappe(list_result=rows))

        assert build_tool("ToDo", "list")["fn"]() == rows

    def test_handler_raises_when_permission_denied(self, monkeypatch):
        monkeypatch.setattr(doctype_module, "_frappe", lambda: _fake_frappe(permission=False))
        with pytest.raises(PermissionError):
            build_tool("ToDo", "list")["fn"]()

    def test_check_permissions_false_skips_the_check(self, monkeypatch):
        # Confirms we don't hit has_permission before the DB call at all.
        def has_permission(*a, **k):
            raise AssertionError("permission should not have been checked")

        fake = SimpleNamespace(
            has_permission=has_permission,
            db=SimpleNamespace(get_list=lambda dt, **k: []),
        )
        monkeypatch.setattr(doctype_module, "_frappe", lambda: fake)

        build_tool("ToDo", "list", check_permissions=False)["fn"]()
