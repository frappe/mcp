"""Translate Frappe DocType fields into JSON Schema fragments.

Frappe speaks fieldtypes ("Currency", "Link", "Check"); MCP clients speak
JSON Schema. Bridging that gap is what lets `expose_doctype()` (upcoming)
auto-generate LLM-callable tools from a DocType's metadata.
"""

from __future__ import annotations

from typing import Any

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
