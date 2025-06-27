# Frappe MCP

Frappe MCP allows your Frappe Framework app to function as an MCP server.

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
> Frappe Framework is not async, it makes use of Werkzeug, a WSGI server, and so
> a from scratch implementation was needed.

_On GitHub, click the Index button on the top right to view the index._

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

#### Register tools with `@mcp.tool`

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

#### Register end point using `@mcp.register`

You use the instantiated object to mark a function as the _entry point_ to your
MCP server, i.e. the function end point will be where your MCP server is served
from.

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
> def handle_mcp(): ...
> ```
>
> **This bypasses auth, so make sure you don't do this in production.**

### Tools

You can register tools, in the following ways:

1. Using the `@mcp.tool` decorator
2. Using the `mcp.add_tool` method

#### `@mcp.tool` decorator

The `@mcp.tool` decorator registers a function as a tool that can be used by an LLM.

The decorator accepts the following optional arguments:

- `name` (optional `str`): The name of the tool. If not provided, the function's `__name__` will be used.
- `description` (optional `str`): A description of what the tool does. If not provided, it will be extracted from the function's docstring.
- `input_schema` (optional `dict`): The JSON schema for the tool's input. If not provided, it will be inferred from the function's signature and docstring.
- `use_entire_docstring` (optional `bool`): If `True`, the entire docstring will be used as the tool's description. Otherwise, only the first section is used (i.e. no `Args`). Defaults to `False`.
- `annotations` (optional `dict`): Additional context about the tool, such as validation information or examples of how to use it. This should be a dictionary conforming to the `ToolAnnotations` `TypedDict` structure.

**Example:**

```python
from frappe_mcp import ToolAnnotations, MCP

mcp = MCP()

annotations = ToolAnnotations(
  title="Get Current Weather",
  readOnlyHint=True,
)

@mcp.tool(annotations=annotations)
def get_current_weather(location: str, unit: str = "celsius"):
    '''Get the current weather in a given location.'''
    # ... implementation ...
```


#### `mcp.add_tool` method

The `mcp.add_tool` method allows for manuall defining a tool, serving as an alternative to the `@mcp.tool` decorator.

It takes a `Tool` object as as arg.

**Example:**

```python
from frappe_mcp import Tool, MCP

mcp = MCP()

def get_current_weather(location: str, unit: str = "celsius"):
    '''Get the current weather in a given location.'''
    # ... implementation ...

# Create a tool object
weather_tool = Tool(
    name="get_current_weather",
    description="...",
    input_schema={'type':'object', 'properties':{ ... }},
    output_schema=None,
    annotations=None,
    fn=get_current_weather,
)

# Add the tool to the MCP instance
mcp.add_tool(weather_tool)
```

#### Tool Annotations

The `ToolAnnotations` can be used to provide additional tool annotations
defined by the MCP spec
([reference](https://modelcontextprotocol.io/docs/concepts/tools#tool-annotations)).

```python
class ToolAnnotations(TypedDict, total=False):
    title: str | None
    readOnlyHint: bool | None
    destructiveHint: bool | None
    idempotentHint: bool | None
    openWorldHint: bool | None
```


#### Tool Definition

The `Tool` object that is used when manually defining and registering a tool
using `mcp.add_tool`.

```python
class Tool(TypedDict):
    name: str
    description: str
    input_schema: dict[str, Any]
    output_schema: dict[str, Any] | None
    annotations: ToolAnnotations | None
    fn: Callable
```

### MCP

## CLI

## Test Endpoints
