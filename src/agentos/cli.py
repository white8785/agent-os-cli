"""AgentOS CLI - Command Line Interface for AgentOS management.

This module provides the main CLI application built with Typer that offers
centralized management for AgentOS installations, updates, and configuration.

The CLI maintains full backward compatibility with existing bash scripts while
providing a modern, type-safe Python interface with rich output formatting.

Commands:
    install: Install AgentOS base and/or project configurations
    update: Update existing AgentOS installations
    uninstall: Remove AgentOS installations
    version: Display version and installation status information

Example:
    Basic CLI usage:

    $ agentos install --project --claude-code
    $ agentos update
    $ agentos uninstall --project
    $ agentos --version
"""

from __future__ import annotations

import os
import sys

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from . import __version__
from .core.config import ConfigManager
from .core.installer import Installer
from .types import InstallationError, InstallLocation, InstallOptions

# Initialize CLI application
app = typer.Typer(
    name="agentos",
    help="🤖 AgentOS - Spec-driven agentic development system",
    add_completion=True,
    rich_markup_mode="rich",
    context_settings={"help_option_names": ["-h", "--help", "help"]},
)

# Initialize Rich console for beautiful output
# In test environments, disable terminal formatting to ensure consistent output
console = Console(
    force_terminal=not bool(os.getenv("CI") or os.getenv("PYTEST_CURRENT_TEST")), width=120, legacy_windows=False
)

# Initialize core components
config_manager = ConfigManager()
installer = Installer(config_manager=config_manager, console=console)


@app.command()
def version() -> None:
    """Display version information and installation status.

    Shows the current AgentOS CLI version along with information about
    any existing base or project installations.

    Example:
        $ agentos version
        AgentOS CLI v1.4.2
        Base installation: v1.4.2
        Project installation: Not found
    """
    # Get installation status
    try:
        status = config_manager.get_install_status()
    except Exception:
        # If we can't get status, show basic version info
        status = None

    # Create a beautiful version display
    table = Table(show_header=False, box=None, padding=(0, 1))
    table.add_column("Label", style="bold blue")
    table.add_column("Value", style="green")

    table.add_row("AgentOS CLI", f"v{__version__}")

    if status:
        if status.base_installed:
            base_version = status.base_version or "unknown"
            table.add_row("Base Installation", f"✅ v{base_version}")
        else:
            table.add_row("Base Installation", "❌ Not installed")

        if status.project_installed:
            agents = ", ".join(agent.value for agent in status.project_agents) or "none"
            table.add_row("Project Installation", f"✅ Agents: {agents}")
            if status.project_type:
                table.add_row("Project Type", status.project_type)
        else:
            table.add_row("Project Installation", "❌ Not installed")
    else:
        table.add_row("Status", "Unable to determine installation status")

    table.add_row("Phase Status", "✅ Phase 2 Complete - Core Implementation")

    panel = Panel(
        table,
        title="🤖 AgentOS Version Information",
        border_style="blue",
        padding=(1, 2),
    )

    console.print(panel)


@app.command()
def install(
    project_only: bool = typer.Option(
        False,
        "--project",
        help="Install to current project only (skip base installation)",
    ),
    claude_code: bool = typer.Option(
        False,
        "--claude-code",
        help="Enable Claude Code integration",
    ),
    cursor: bool = typer.Option(
        False,
        "--cursor",
        help="Enable Cursor integration",
    ),
    project_type: str = typer.Option(
        "default",
        "--project-type",
        help="Project type for customized setup",
    ),
    overwrite_instructions: bool = typer.Option(
        False,
        "--overwrite-instructions",
        help="Overwrite existing instruction files",
    ),
    overwrite_standards: bool = typer.Option(
        False,
        "--overwrite-standards",
        help="Overwrite existing standards files",
    ),
    overwrite_config: bool = typer.Option(
        False,
        "--overwrite-config",
        help="Overwrite existing config.yml",
    ),
) -> None:
    """Install AgentOS base installation and/or project configuration.

    This command installs AgentOS components either system-wide (base)
    or in the current project. By default, installs base first, then
    optionally prompts for project installation.

    Examples:
        Install base system and prompt for project:
        $ agentos install

        Install to current project only:
        $ agentos install --project --claude-code

        Install with specific project type:
        $ agentos install --project-type python-web --claude-code
    """
    try:
        # Determine installation location
        location = InstallLocation.PROJECT if project_only else InstallLocation.BASE

        # Create install options
        options = InstallOptions(
            location=location,
            claude_code=claude_code,
            cursor=cursor,
            project_type=project_type,
            overwrite_instructions=overwrite_instructions,
            overwrite_standards=overwrite_standards,
            overwrite_config=overwrite_config,
        )

        # Handle base installation with project prompt
        if location == InstallLocation.BASE:
            # Install base first
            installer.install(options)

            # Prompt for project installation
            if typer.confirm("\n🤔 Install AgentOS to current project as well?"):
                project_options = InstallOptions(
                    location=InstallLocation.PROJECT,
                    claude_code=claude_code,
                    cursor=cursor,
                    project_type=project_type,
                    overwrite_instructions=overwrite_instructions,
                    overwrite_standards=overwrite_standards,
                    overwrite_config=overwrite_config,
                )
                installer.install(project_options)
        else:
            # Project-only installation
            installer.install(options)

    except InstallationError as e:
        console.print(f"❌ [bold red]Installation failed:[/bold red] {e}")
        sys.exit(1)
    except Exception as e:
        console.print(f"❌ [bold red]Unexpected error during installation:[/bold red] {e}")
        sys.exit(1)


@app.command()
def update(
    project_only: bool = typer.Option(
        False,
        "--project",
        help="Update current project installation only",
    ),
) -> None:
    """Update existing AgentOS installations.

    Updates AgentOS components to the latest version. Can update
    base installation, project installation, or both.

    Examples:
        Update base installation:
        $ agentos update

        Update project installation only:
        $ agentos update --project
    """
    try:
        installer.update(project_only=project_only)
    except InstallationError as e:
        console.print(f"❌ [bold red]Update failed:[/bold red] {e}")
        sys.exit(1)
    except Exception as e:
        console.print(f"❌ [bold red]Unexpected error during update:[/bold red] {e}")
        sys.exit(1)


@app.command()
def uninstall(
    project_only: bool = typer.Option(
        False,
        "--project",
        help="Remove from current project only",
    ),
) -> None:
    """Remove AgentOS installations.

    Removes AgentOS components from the system. Can remove base
    installation, project installation, or both.

    Examples:
        Remove base installation:
        $ agentos uninstall

        Remove project installation only:
        $ agentos uninstall --project
    """
    try:
        installer.uninstall(project_only=project_only)
    except InstallationError as e:
        console.print(f"❌ [bold red]Uninstall failed:[/bold red] {e}")
        sys.exit(1)
    except Exception as e:
        console.print(f"❌ [bold red]Unexpected error during uninstall:[/bold red] {e}")
        sys.exit(1)


def main() -> None:
    """Main entry point for the AgentOS CLI application.

    This function serves as the entry point defined in pyproject.toml
    and handles any top-level application setup or error handling.
    """
    try:
        app()
    except KeyboardInterrupt:
        console.print("\n👋 [yellow]AgentOS CLI interrupted by user[/yellow]")
        sys.exit(130)  # Standard exit code for Ctrl+C
    except InstallationError as e:
        console.print(f"❌ [bold red]AgentOS error:[/bold red] {e}")
        sys.exit(1)
    except Exception as e:
        console.print(f"❌ [bold red]Unexpected error:[/bold red] {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
