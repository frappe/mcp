"""Auto-generate MCP tools from a Frappe DocType.

Public surface:
    expose_doctype(mcp, doctype, ...)  — register CRUD-ish tools on `mcp`
    build_tool(doctype, operation)     — build one Tool for one op

Frappe speaks fieldtypes ("Currency", "Link", "Check"); MCP clients speak
JSON Schema. This module bridges them so hand-written and auto-generated
tools follow the same code path.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import TYPE_CHECKING, Any

from frappe_mcp.server.tools import Tool, ToolOptions, get_tool

if TYPE_CHECKING:
    from frappe_mcp.server.server import MCP


# Operations exposed by expose_doctype() when the caller doesn't specify.
# Delete is deliberately excluded — opt in explicitly.
DEFAULT_OPERATIONS: tuple[str, ...] = ("get", "list", "create", "update")

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
        case "list":
            return _list(doctype, check_permissions=check_permissions)
        case "create":
            return _create(doctype, check_permissions=check_permissions)
        case "update":
            return _update(doctype, check_permissions=check_permissions)
        case "delete":
            return _delete(doctype, check_permissions=check_permissions)
        case _:
            raise ValueError(f"Unsupported operation: {operation!r}")


def _get(doctype: str, *, check_permissions: bool) -> Tool:
    def handler(name: str) -> dict[str, Any]:
        if check_permissions:
            _require_permission(doctype, "read", doc=name)
        return _frappe().get_doc(doctype, name).as_dict()

    handler.__name__ = f"get_{_snake(doctype)}"
    handler.__doc__ = (
        f"Get a {doctype} by name.\n"
        f"\n"
        f"Args:\n"
        f"    name: {doctype} name."
    )
    return get_tool(handler, ToolOptions(annotations={"readOnlyHint": True}))


_DEFAULT_LIST_LIMIT = 20


def _list(doctype: str, *, check_permissions: bool) -> Tool:
    def handler(
        filters: dict | None = None,
        fields: list[str] | None = None,
        limit: int = _DEFAULT_LIST_LIMIT,
        offset: int = 0,
        order_by: str | None = None,
    ) -> list[dict[str, Any]]:
        if check_permissions:
            _require_permission(doctype, "read")
        return _frappe().db.get_list(
            doctype,
            filters=filters or {},
            fields=fields or ["name"],
            limit=limit,
            start=offset,
            order_by=order_by,
        )

    handler.__name__ = f"list_{_snake(doctype)}"
    handler.__doc__ = (
        f"List {doctype} records with optional filters, fields, limit, and ordering.\n"
        f"\n"
        f"Args:\n"
        f"    filters: Frappe filters, e.g. {{'status': 'Open'}}.\n"
        f"    fields: Fieldnames to return; defaults to ['name'].\n"
        f"    limit: Max rows to return (default {_DEFAULT_LIST_LIMIT}).\n"
        f"    offset: Row offset for pagination.\n"
        f"    order_by: e.g. 'modified desc'."
    )

    tool = get_tool(handler, ToolOptions(annotations={"readOnlyHint": True}))
    # Semantic constraints the type system can't express.
    tool["input_schema"]["properties"]["limit"]["minimum"] = 1
    tool["input_schema"]["properties"]["offset"]["minimum"] = 0
    return tool


class _LazyDict(dict):
    """A dict that runs its factory on first read.

    Used to defer `frappe.get_meta` from build_tool() time to the first
    time an MCP client actually asks for the schema — so tool
    registration stays Frappe-free and consistent with get/list/delete.
    Result is cached on the instance after the first resolve.
    """

    def __init__(self, factory):
        super().__init__()
        self._factory = factory

    def _resolve(self):
        f = self._factory
        if f is None:
            return
        self._factory = None
        dict.update(self, f())

    def __getitem__(self, key):
        self._resolve()
        return dict.__getitem__(self, key)

    def __contains__(self, key):
        self._resolve()
        return dict.__contains__(self, key)

    def __iter__(self):
        self._resolve()
        return dict.__iter__(self)

    def __len__(self):
        self._resolve()
        return dict.__len__(self)

    def get(self, key, default=None):
        self._resolve()
        return dict.get(self, key, default)

    def keys(self):
        self._resolve()
        return dict.keys(self)

    def values(self):
        self._resolve()
        return dict.values(self)

    def items(self):
        self._resolve()
        return dict.items(self)


def _writable_field_schemas(doctype: str) -> tuple[dict[str, dict], list[str]]:
    """Build (properties, required) for a `doctype` at build time.

    Skips Frappe's NO_VALUE_FIELDS (Section Break, HTML, Table, ...) and
    DEFAULT_FIELDS (owner, creation, modified, ...) that the framework
    manages itself. Fields with `reqd=1` end up in the required list.
    """
    frappe = _frappe()
    properties: dict[str, dict] = {}
    required: list[str] = []
    for field in frappe.get_meta(doctype).fields:
        fieldtype = field.get("fieldtype")
        fieldname = field.get("fieldname")
        if not fieldname or fieldtype in frappe.model.NO_VALUE_FIELDS:
            continue
        if fieldname in frappe.model.DEFAULT_FIELDS:
            continue
        properties[fieldname] = frappe_fieldtype_to_json_schema(field)
        if field.get("reqd"):
            required.append(fieldname)
    return properties, required


def _create(doctype: str, *, check_permissions: bool) -> Tool:
    def _build_schema() -> dict[str, Any]:
        properties, required = _writable_field_schemas(doctype)
        schema: dict[str, Any] = {"type": "object", "properties": properties}
        if required:
            schema["required"] = required
        return schema

    input_schema = _LazyDict(_build_schema)

    def handler(**values: Any) -> dict[str, Any]:
        if check_permissions:
            _require_permission(doctype, "create")
        doc = _frappe().get_doc({"doctype": doctype, **values})
        doc.insert()
        return doc.as_dict()

    return Tool(
        name=f"create_{_snake(doctype)}",
        description=f"Create a new {doctype}.",
        input_schema=input_schema,
        output_schema=None,
        annotations={"readOnlyHint": False},
        fn=handler,
    )


def _update(doctype: str, *, check_permissions: bool) -> Tool:
    def _build_schema() -> dict[str, Any]:
        properties, _ = _writable_field_schemas(doctype)
        properties = {
            "name": {"type": "string", "description": f"{doctype} name"},
            **properties,
        }
        return {"type": "object", "properties": properties, "required": ["name"]}

    input_schema = _LazyDict(_build_schema)

    def handler(name: str, **values: Any) -> dict[str, Any]:
        if check_permissions:
            _require_permission(doctype, "write", doc=name)
        frappe = _frappe()
        doc = frappe.get_doc(doctype, name)
        for k, v in values.items():
            doc.set(k, v)
        doc.save()
        return doc.as_dict()

    return Tool(
        name=f"update_{_snake(doctype)}",
        description=f"Update fields on an existing {doctype}. Only pass fields you want to change.",
        input_schema=input_schema,
        output_schema=None,
        annotations={"readOnlyHint": False},
        fn=handler,
    )


def _delete(doctype: str, *, check_permissions: bool) -> Tool:
    def handler(name: str) -> dict[str, Any]:
        if check_permissions:
            _require_permission(doctype, "delete", doc=name)
        _frappe().delete_doc(doctype, name)
        return {"deleted": True, "doctype": doctype, "name": name}

    handler.__name__ = f"delete_{_snake(doctype)}"
    handler.__doc__ = (
        f"Delete a {doctype} by name. Irreversible.\n"
        f"\n"
        f"Args:\n"
        f"    name: {doctype} name."
    )
    return get_tool(
        handler,
        ToolOptions(annotations={"readOnlyHint": False, "destructiveHint": True}),
    )


def expose_doctype(
    mcp: MCP,
    doctype: str,
    *,
    operations: Sequence[str] = DEFAULT_OPERATIONS,
    check_permissions: bool = True,
) -> None:
    """Register one MCP tool per `operations` entry for `doctype` on `mcp`.

    Example:
        mcp = frappe_mcp.MCP("my-server")
        expose_doctype(mcp, "ToDo")
        # → registers get_todo, list_todo, create_todo, update_todo

        expose_doctype(mcp, "ToDo", operations=("get", "list"))       # read-only
        expose_doctype(mcp, "ToDo", operations=(*DEFAULT_OPERATIONS, "delete"))
    """
    for op in operations:
        mcp.add_tool(build_tool(doctype, op, check_permissions=check_permissions))
