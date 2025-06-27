# Frappe MCP

Frappe MCP allows your Frappe Framework app to function as an MCP server that
can handle MCP requests.

```python
# app/app/mcp.py
import frappe_mcp

mcp = frappe_mcp.MCP("todo-mcp")

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
> The official Python SDK only supports async Python, i.e. it assumes that your
> server is an ASGI server.
>
> Frappe Framework is not async, it makes use of Werkzeug, a WSGI server and so
> a from scratch implementation was needed.

## Installation

<!--
You install Frappe MCP like any other dependency Python dependency.

```bash
uv add frappe-mcp
```

or

```bash
pip install frappe-mcp
```

Then update your `pyproject.toml` to include Frappe MCP
-->

## Limitations

<!-- Add -->

### Authentication

### Type Annotations

## Not yet implemented

## Auth

Yet to be implemented.

## Documentation

Frappe MCP is fairly straightforward to use. Most of the MCP specific heavy
lifting is handled for you.

### Basic Usage

To use `frappe-mcp` you first create an instance of the `mcp` object:

```python
# app/app/mcp.py (same dir as hooks.py)
import frappe_mcp

mcp = frappe_mcp.MCP("your-app-mcp")
```

Each instance of an `MCP` object can be used to register a single MCP endpoint.

You can create multiple of these objects if you need to serve multiple MCP
endpoints for instance to group functionality.

#### `mcp.tool`

You use the instaniated object i.e. `mcp` to register tools:

```python
# app/app/tools/tools.py
from app.mcp import mcp

@mcp.tool()
def tool_name(a: int, b: str):
  """Description of what the tool does

  Args:
      a: Description for arg `a`.
      b: Description for arg `b`.
  """
  ... # tool body

  return value
```

> [!TIP]
>
> Using Google style docstrings and type annotations like in the example above
> allows Frappe MCP to extract the `inputSchema` for the tool without any additional
> configuration.

If needed, you can manually provide the `inputSchema` and other meta data like annotations.
Check the [Tools](#tools) section for more details.

#### `mcp.register`

You use the instantiated object to mark a function as the _entry point_ to your MCP server.

```python
# app/app/mcp.py
@mcp.register()
def handle_mcp():
  import app.tools.tools # ensures that your tools are registered
```

Once this is done, your MCP server should be serving at the REST endpoint for
the method ([docs](https://docs.frappe.io/framework/user/en/api/rest#remote-method-calls)).

In this case the endpoint when running locally would be:

```
http://<SITE_NAME:PORT>/api/method/app.mcp.handle_mcp
```

> [!WARNING]
>
> The function body's **only purpose is to import files containing your tools**.
> If this is not done your tools will not be loaded as Frappe MCP does not know where
> your tools are located.
>
> If your tools are in the same file, or have been imported globally, you can
> leave the function body empty.

> [!NOTE]
>
> Due to current limitations of the Framework, while running the locally
> for development purposes, you may set the `allow_guests` flag, i.e:
>
> ```python
> @mcp.register(allow_guests=True)
> ```
>
> **This bypasses auth, so make sure you don't do this in production.**

### MCP

### Tools

## CLI

## Test Endpoints
