# Frappe MCP

Frappe MCP allows your Frappe Framework app to function as an MCP server that
can handle MCP requests.

```python
# app/app/mcp.py
from frappe_mcp.server import MCP

mcp = MCP("todo-mcp")

@mcp.tool()
def fetch_todos(username: str): ...

@mcp.tool()
def mark_done(name: str): ...

# MCP end point at: http://<BASE_URL>/api/method/app.mcp.handle_mcp
@mcp.register()
def handle_mcp(): ...
```

> [!NOTE]
>
> **Why not use the official Python SDK?**
>
> Official Python SDK only supports async Python, i.e. it assumes that your
> server is an ASGI server. Frappe Framework is not async, it makes use of
> Werkzeug, a WSGI server and so a from scratch implementation was needed.

## Installation

You install Frappe MCP like any other dependency Python dependency.

```bash
uv add frappe-mcp
```

or

```bash
pip install frappe-mcp
```

Then update your `pyproject.toml` to include Frappe MCP

## Limitations

<!-- Add -->

## Not yet implemented

## Auth

Yet to be implemented.

## Documentation

### Usage

### MCP

### Tools

## CLI

## Test Endpoints
