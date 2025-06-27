import click

from frappe_mcp.cli import utils


@click.group(invoke_without_command=True)
@click.pass_context
def run(ctx):
    """Frappe MCP CLI tool"""
    if ctx.invoked_subcommand is None:
        ctx.invoke(check)


@run.command()
def version():
    """Print version information"""
    version = get_version()
    click.echo(version)


@run.command()
@click.option('--app', '-a', help='Check only a specific app')
@click.option('--verbose', '-v', is_flag=True, help='Show detailed information')
def check(app: str | None = None, verbose: bool = False):
    """Check if Frappe MCP is being used correctly"""
    try:
        import frappe  # noqa: F401
    except ImportError:
        click.secho('Not running in a Frappe site', fg='red')
        return

    if not app:
        apps = utils.get_apps_using_frappe_mcp()
        if apps:
            click.echo(
                f'Found [{click.style(", ".join(apps), bold=True)}] that may be using {click.style("frappe_mcp", "blue")}'
            )
            print()
    else:
        apps = [app]

    if not apps:
        click.secho('No apps found using frappe_mcp', fg='yellow')

    for i, app in enumerate(apps):
        handlers = utils.find_mcp_handlers_in_app(app)
        if not handlers:
            click.echo(f'No MCP handler found for {click.style(app, bold=True)}')
            continue

        utils.check(app, handlers, verbose)

        if i < len(apps) - 1:
            print()


def get_version():
    from pathlib import Path

    import tomllib

    pyproject_path = Path(__file__).parent.parent.parent / 'pyproject.toml'
    with open(pyproject_path, 'rb') as f:
        pyproject = tomllib.load(f)
    return pyproject['project']['version']
