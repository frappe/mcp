from __future__ import annotations

import json
from pathlib import Path
from textwrap import indent

import click

from frappe_mcp.server import MCP

dim_bullet = click.style('*', dim=True)
green_check = click.style('✓', fg='green')
red_x = click.style('✗', fg='red')
yellow_o = click.style('o', fg='yellow')


def check(app: str, handlers: list[tuple[Path, MCP]], verbose: bool = False):
    if not len(handlers):
        return

    click.secho(app + ':', bold=True)
    for p, m in handlers:
        path = get_app_relative_path(app, p)
        if m._mcp_entry_fn is None:
            click.echo(f'{dim_bullet} handler not properly registered: {path} {red_x}')
            continue

        mcp_url = get_mcp_url(m._mcp_entry_fn)
        click.echo(
            f'{dim_bullet} handler: {click.style(m._mcp_entry_fn.__name__, fg="cyan")} {green_check}'
        )
        click.echo(f'{dim_bullet} url: {mcp_url} {green_check}')

        try:
            m._mcp_entry_fn()
            click.echo(f'{dim_bullet} handler called {green_check}')

        except Exception as e:
            click.echo(f'{dim_bullet} handler error: {e} {red_x}')
            continue

        for name, tool in m._tool_registry.items():
            all_good = True
            click.echo(f'{dim_bullet} tool {click.style(name, bold=True)}:', nl=verbose)

            nl_fix = lambda: all_good and not verbose and print()  # noqa: B023, E731

            if not tool['description']:
                nl_fix()
                click.echo(f'  {dim_bullet} description not set {yellow_o}')
                all_good = False
            if tool['description'] and verbose:
                click.echo(f'  {dim_bullet} description:')
                click.echo(indent(tool['description'], '    '))

            if not tool['annotations'] and verbose:
                click.echo(f'  {dim_bullet} annotations not set {yellow_o}')
                all_good = False

            props = tool['input_schema'].get('properties')
            if not props:
                nl_fix()
                click.echo(f'  {dim_bullet} input_schema properties not set {yellow_o}')
                all_good = False

            assert isinstance(props, dict), 'input schema properties should be a dict'

            for k, v in props.items():
                desc = v.get('description')
                typ = v.get('type')
                arg = click.style(k, bold=True)

                if not typ:
                    nl_fix()
                    click.echo(f'    {dim_bullet} arg {arg} type not set {yellow_o}')
                    all_good = False

                if not desc:
                    nl_fix()
                    click.echo(
                        f'  {dim_bullet} arg {arg} description not set {yellow_o}'
                    )
                    all_good = False

            if verbose and tool['input_schema']:
                click.echo(f'  {dim_bullet} input_schema:')
                click.echo(indent(json.dumps(tool['input_schema'], indent=2), '    '))

            if verbose and tool['output_schema']:
                click.echo(f'  {dim_bullet} output_schema:')
                click.echo(indent(json.dumps(tool['output_schema'], indent=2), '    '))

            if verbose and tool['annotations']:
                click.echo(f'  {dim_bullet} annotations:')
                click.echo(indent(json.dumps(tool['annotations'], indent=2), '    '))

            if all_good:
                if verbose:
                    click.echo(f'  {dim_bullet} all good {green_check}')
                else:
                    click.echo(f' {green_check}')


def get_mcp_url(mcp_entry_fn) -> str:
    handler_path = '.'.join([mcp_entry_fn.__module__, mcp_entry_fn.__name__])

    mcp_path = '/'.join(
        [
            '/api/method',
            handler_path,
        ]
    )

    mcp_url = f'{click.style("http://<BASE_URL>", dim=True)}{click.style(mcp_path, fg="cyan")}'

    try:
        from frappe.utils import get_host_name_from_request

        host_name = get_host_name_from_request()
    except ImportError:
        host_name = None

    if host_name:
        host_name.removesuffix('/')
        mcp_url = click.style('/'.join([host_name, mcp_path]), fg='cyan')

    return mcp_url


def get_app_relative_path(app: str, p: Path) -> str:
    import frappe

    app_path = Path(frappe.get_app_path(app))
    return str(p.relative_to(app_path))


def find_mcp_handlers_in_app(app) -> list[tuple[Path, MCP]]:
    import ast
    import importlib
    from pathlib import Path

    import frappe

    path = Path(frappe.get_app_path(app))
    mcp_handlers: list[tuple[Path, MCP]] = []

    if not path.exists():
        return mcp_handlers

    for p in path.rglob('*.py'):
        try:
            with open(p) as f:
                content = f.read()
                if 'frappe_mcp' not in content:
                    continue
                tree = ast.parse(content, filename=str(p))
        except (SyntaxError, UnicodeDecodeError, ValueError):
            # ValueError for files with null bytes
            continue

        for node in ast.walk(tree):
            if not isinstance(node, ast.Assign):
                continue

            # Looking for var = MCP(...)
            if not isinstance(node.value, ast.Call):
                continue

            call_node = node.value
            func = call_node.func

            # Check if this is an MCP call.
            func_name = ''
            if isinstance(func, ast.Name):
                func_name = func.id
            elif isinstance(func, ast.Attribute):
                func_name = func.attr

            if func_name != 'MCP':
                continue

            # We found something like `var = MCP()`. Now get the variable name.
            if not (node.targets and isinstance(node.targets[0], ast.Name)):
                continue

            var_name = node.targets[0].id

            # Construct Python module path to import
            rel_path = p.relative_to(path)
            if rel_path.stem == '__init__':
                module_rel_path = '.'.join(rel_path.parent.parts)
            else:
                module_rel_path = '.'.join((*rel_path.parent.parts, rel_path.stem))

            if module_rel_path:
                module_path = f'{app}.{module_rel_path}'
            else:
                # Top-level __init__.py or module in app root
                module_path = app

            try:
                from frappe_mcp.server import MCP

                module = importlib.import_module(module_path)
                mcp_instance = getattr(module, var_name)
                if isinstance(mcp_instance, MCP):
                    mcp_handlers.append((p, mcp_instance))
            except (ImportError, AttributeError, Exception):
                # Could fail for many reasons, just ignore.
                continue

    return mcp_handlers


def get_apps_using_frappe_mcp() -> list[str]:
    """Find all apps installed on the Frappe bench that depend on frappe-mcp."""
    from pathlib import Path

    import frappe
    import tomllib

    apps_using_mcp = []
    apps_path = Path(frappe.get_app_path('frappe')).parent.parent

    for app_path in apps_path.iterdir():
        if not app_path.is_dir():
            continue

        app = app_path.name
        pyproject_path = app_path / 'pyproject.toml'
        if not pyproject_path.exists():
            continue

        with open(pyproject_path, 'rb') as f:
            try:
                pyproject = tomllib.load(f)
            except tomllib.TOMLDecodeError:
                continue

        dependencies = pyproject.get('project', {}).get('dependencies', [])
        if any('frappe-mcp' in dep for dep in dependencies):
            apps_using_mcp.append(app)
    return apps_using_mcp
