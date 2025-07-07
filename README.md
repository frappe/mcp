# Frappe MCP

Frappe MCP allows your Frappe Framework app to function as a [Streamable HTTP MCP
server](https://modelcontextprotocol.io/specification/2025-06-18/basic/transports#streamable-http).

```python
# app/app/mcp.py
import frappe_mcp

mcp = frappe_mcp.MCP("todo-mcp")

@mcp.tool()
def fetch_todos(username: str): ...

@mcp.tool()
def mark_done(name: str): ...

# MCP endpoint at: http://<BASE_URL>/api/method/app.mcp.handle_mcp
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

Frappe MCP is yet to be published, until then you will have to clone and then
install from dir. For illustration:

```bash
git clone https://github.com/frappe/mcp

cd path/to/bench
source ./env/bin/activate

pip install path/to/cloned/dir/mcp
```

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

Frappe MCP is yet in its infancy, as of now it **only supports** Tools.
Remaining server features such as resources, prompts, tool streaming using SSE
will be added as needed.

## Auth

If you are using a version of the Framework having the OAuth2 updates
([frappe#33188](https://github.com/frappe/frappe/pull/33188)) then using Frappe
MCP with it should be pretty straight forward. You can view this video to check
out how to set up Auth on the MCP Inspector.

https://github.com/user-attachments/assets/a1783a36-7bea-4361-8c7b-bdbb9789877b

If your version does not contain these updates, you will have to register an
OAuth Client on your Framework instance for ht MCP client. You can check the
[docs](https://docs.frappe.io/framework/oauth2) for this.

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

#### Register endpoint using `@mcp.register`

You use the instantiated object to mark a function as the _entry point_ to your
MCP server, i.e. the function endpoint will be where your MCP server is served
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

The `mcp.add_tool` method allows manually defining a tool, serving as an alternative to the `@mcp.tool` decorator.

It takes a `Tool` object as an arg.

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

#### Input Schema

Input schema refers to the [JSON Schema](https://json-schema.org/understanding-json-schema/reference/type) definition that describes a tool's parameters.

The following tool:

```python
@mcp.tool()
def tool_name(a: int, b: str = "default"):
    """Description of what the tool does

    Args:
        a: Description for arg `a`.
        b: Description for arg `b`.
    """
    ... # tool body

    return value
```

will have this input schema:

```json
{
  "type": "object",
  "properties": {
    "a": {
      "type": "integer",
      "description": "Description for arg `a`."
    },
    "b": {
      "type": "string",
      "description": "Description for arg `b`."
    }
  },
  "required": ["a"]
}
```

This input schema is generated from the tool body automatically when using the
decorator.

### MCP

The `MCP` class is the main class for creating an MCP server.

This class orchestrates the handling of JSON-RPC requests, manages a registry of
available tools, and integrates with a WSGI server (like Frappe Framework) to
expose MCP functionality.

In a Frappe application, you would typically create a single instance of this
class and use the `@mcp.register()` decorator on an API endpoint. Tools can be
added using the `@mcp.tool()` decorator.

For use in other Werkzeug-based servers, you can use the `mcp.handle()` method
directly.

#### `mcp.register` decorator

This decorator is used in Frappe applications to designate a function as the
entry point for MCP requests. It wraps the function with the necessary logic to
handle JSON-RPC messages, including initializing the tool registry and routing
requests to the appropriate handlers.

The decorator accepts the following optional arguments:

- `allow_guest` (optional `bool`): If `True`, allows unauthenticated access to the endpoint. Defaults to `False`.
- `xss_safe` (optional `bool`): If `True`, response will not be sanitized for XSS. Defaults to `False`.

**Example:**

```python
# In app/mcp.py
from frappe_mcp import MCP

mcp = MCP(name="my-mcp-server")

@mcp.register()
def handle_mcp():
    '''The entry point for MCP requests.'''
    # This function body is executed before request handling.
    # It's a good place to import modules that register tools.
    import app.tools
```

#### `mcp.handle` method

This method directly processes a `werkzeug.Request` and returns a
`werkzeug.Response`. It's the core request handling logic.

This method can be used to integrate the MCP server into **any Werkzeug-based application**
i.e. even if you're not using Frappe Framework, you can use this to handle MCP
endpoints in your server.

It accepts the following arguments:

- `request`: The `werkzeug.Request` object containing the MCP request.
- `response`: A `werkzeug.Response` object to be populated with the MCP response.

It returns the populated `werkzeug.Response` object.

## CLI

Frappe MCP comes with a handy CLI tool to help you verify that your MCP server is set up correctly.

<img width="436" alt="check" src="https://github.com/user-attachments/assets/a8e1481a-5388-4976-9728-404677381a07" />

Its `check` command inspects your Frappe apps to ensure that `frappe_mcp` is being used correctly. This is also the default command, so you can run it with `frappe-mcp` or `frappe-mcp check`.

It performs the following checks:

- Verifies that it's running within a Frappe environment.
- Finds all apps that are potentially using `frappe_mcp`.
- For each app, it discovers MCP handlers.
- It then checks the handlers and their tools for correctness.

**Options:**

- `--app`, `-a`': Check only a specific app.
- `--verbose`, `-v`: Show detailed information such as the input schema.

**Usage:**

```bash
# After installing frappe-mcp and using it in your app

# In your frappe bench dir so that you can use the cli
source ./env/bin/activate

# Check all apps that might be using Frappe MCP
frappe-mcp

# Check specific app with verbose output
frappe-mcp check --app app_name --verbose
```

## Testing against Inspector

You can use the official
[inspector](https://github.com/modelcontextprotocol/inspector) tool to verify if
your MCP endpoints are being served correctly.

![inspector](https://github.com/user-attachments/assets/64e13ed4-0170-48b4-8b35-530e0f713a29)

Make sure to:

1. Set **Transport** to **Streamable HTTP**.
2. Set **URL** to your MCP endpoint (you can use the CLI command `frappe-mcp check` to get it).
3. Navigate to Auth Settings then click on **Quick OAuth Flow**

After this you'll be prompted to login and authorize the client after which you
can use it to test out your MCP server.

> [!NOTE]
>
> You may skip the final step by setting the `allow_guests` flag, i.e:
>
> ```python
> @mcp.register(allow_guests=True)
> def handle_mcp(): ...
> ```
>
> **This bypasses auth, so make sure you don't do this in production.**
