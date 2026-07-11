"""Translate Frappe DocType fields into JSON Schema fragments.

Frappe speaks fieldtypes ("Currency", "Link", "Check"); MCP clients speak
JSON Schema. Bridging that gap is what lets `expose_doctype()` (upcoming)
auto-generate LLM-callable tools from a DocType's metadata.
"""

from __future__ import annotations

from typing import Any

from frappe_mcp.server.tools import Tool

# Not derived from `frappe.model.numeric_fieldtypes` etc. — Frappe's groupings
# classify by DB storage, not JSON Schema shape: Check would fall in as int,
# Rating wouldn't fall in at all.
_BASE_SCHEMAS: dict[str, dict[str, Any]] = {
    "Check": {"type": "boolean"},  # Frappe stores 0/1; JSON bool is nicer for LLMs.
    "Int": {"type": "integer"},
    "Long Int": {"type": "integer"},
    "Float": {"type": "number"},
    "Currency": {"type": "number"},
    "Percent": {"type": "number"},
    "Rating": {"type": "number"},
    "Date": {"type": "string", "format": "date"},
    "Datetime": {"type": "string", "format": "date-time"},
    "Time": {"type": "string", "format": "time"},
}


def frappe_fieldtype_to_json_schema(field: dict[str, Any]) -> dict[str, Any]:
    """One entry for a tool's `inputSchema.properties[field.fieldname]`.

    Reads only `fieldtype`, `options`, `label`, `fieldname` from `field`.
    Select gets an `enum`; Link/Dynamic Link get an `x-frappe-link-doctype`
    hint carrying the target DocType.
    """
    fieldtype = field.get("fieldtype") or "Data"

    if fieldtype == "Select":
        schema = _select_schema(field)
    elif fieldtype in ("Link", "Dynamic Link"):
        schema = _link_schema(field)
    else:
        schema = dict(_BASE_SCHEMAS.get(fieldtype, {"type": "string"}))

    return _with_label(schema, field)


def _select_schema(field: dict[str, Any]) -> dict[str, Any]:
    # Frappe stores Select options as a newline-separated string.
    raw = (field.get("options") or "").strip()
    options = [line.strip() for line in raw.splitlines() if line.strip()]
    schema: dict[str, Any] = {"type": "string"}
    if options:
        schema["enum"] = options
    return schema


def _link_schema(field: dict[str, Any]) -> dict[str, Any]:
    schema: dict[str, Any] = {"type": "string"}
    target = (field.get("options") or "").strip()
    if target:
        schema["x-frappe-link-doctype"] = target
    return schema


def _with_label(schema: dict[str, Any], field: dict[str, Any]) -> dict[str, Any]:
    if "description" not in schema:
        label = (field.get("label") or field.get("fieldname") or "").strip()
        if label:
            schema["description"] = label
    return schema


def _frappe():
    # Lazy: keep this module importable without a bench, so pure helpers stay
    # unit-testable and the Frappe dependency is confined to the tool handlers.
    import frappe
    return frappe


def _snake(doctype: str) -> str:
    # Matches frappe.scrub: whitespace -> underscore, lowercased.
    return doctype.replace(" ", "_").lower()


def _require_permission(doctype: str, ptype: str, *, doc: str | None = None) -> None:
    """Raise `PermissionError` if the current user can't `ptype` on `doctype`."""
    frappe = _frappe()
    if frappe.has_permission(doctype, ptype=ptype, doc=doc, throw=False):
        return
    target = f"{doctype} '{doc}'" if doc else doctype
    raise PermissionError(f"No {ptype} permission on {target}")


def build_tool(doctype: str, operation: str, *, check_permissions: bool = True) -> Tool:
    """Return the MCP Tool spec for one `operation` on `doctype`.

    A spec — this doesn't call Frappe. Frappe is invoked only when a client
    (Claude, an MCP Inspector session, ...) actually calls the returned tool.
    """
    match operation:
        case "get":
            return _get(doctype, check_permissions=check_permissions)
        case _:
            raise ValueError(f"Unsupported operation: {operation!r}")


def _get(doctype: str, *, check_permissions: bool) -> Tool:
    input_schema = {
        "type": "object",
        "properties": {"name": {"type": "string", "description": f"{doctype} name"}},
        "required": ["name"],
    }

    def handler(name: str) -> dict[str, Any]:
        if check_permissions:
            _require_permission(doctype, "read", doc=name)
        return _frappe().get_doc(doctype, name).as_dict()

    return Tool(
        name=f"get_{_snake(doctype)}",
        description=f"Get a {doctype} by name.",
        input_schema=input_schema,
        output_schema=None,
        annotations={"readOnlyHint": True},
        fn=handler,
    )
