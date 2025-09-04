"""Installation logic for AgentOS.

This module provides the core installation, update, and uninstall logic for
AgentOS, coordinating between configuration management and shell script execution
while providing a clean, type-safe interface.

The Installer class handles:
- Base and project installation orchestration
- Update and uninstall operations
- Version checking and GitHub API integration
- Installation validation and status reporting
- Comprehensive error handling and recovery

Example:
    >>> from agent_os_cli.core.installer import Installer
    >>> from agent_os_cli.types import InstallOptions, InstallLocation
    >>> installer = Installer()
    >>> options = InstallOptions(location=InstallLocation.BASE, claude_code=True)
    >>> installer.install(options)
"""

from __future__ import annotations

import json
import shutil
from typing import Any

import requests
from rich.console import Console

from ..types import InstallationError, InstallLocation, InstallOptions
from .config import ConfigManager
from .shell import ShellExecutor


class Installer:
    """Manages AgentOS installation, update, and uninstall operations.

    The Installer class provides the high-level interface for all AgentOS
    lifecycle operations, coordinating between configuration management
    and shell script execution while providing comprehensive error handling.

    Attributes:
        config_manager: Configuration management instance
        shell_executor: Shell script execution instance
        console: Rich console for formatted output

    Example:
        >>> installer = Installer()
        >>> status = installer.get_install_status()
        >>> if not status.base_installed:
        ...     installer.install(InstallOptions(location=InstallLocation.BASE))
    """

    def __init__(
        self,
        config_manager: ConfigManager | None = None,
        shell_executor: ShellExecutor | None = None,
        console: Console | None = None,
    ) -> None:
        """Initialize installer with dependencies.

        Args:
            config_manager: Optional ConfigManager instance
            shell_executor: Optional ShellExecutor instance
            console: Optional Rich console instance
        """
        self.console = console or Console()
        self.config_manager = config_manager or ConfigManager()
        self.shell_executor = shell_executor or ShellExecutor(self.console)

    def install(self, options: InstallOptions) -> None:
        """Install AgentOS components based on provided options.

        Orchestrates the installation process, handling both base and project
        installations with appropriate validation and error handling.

        Args:
            options: Installation configuration options

        Raises:
            InstallationError: If installation fails at any stage

        Example:
            >>> from agent_os_cli.types import InstallOptions, InstallLocation
            >>> installer = Installer()
            >>> options = InstallOptions(
            ...     location=InstallLocation.PROJECT,
            ...     claude_code=True,
            ...     project_type="python"
            ... )
            >>> installer.install(options)
        """
        if options.location == InstallLocation.BASE:
            self._install_base(options)
        elif options.location == InstallLocation.PROJECT:
            self._install_project(options)
        else:
            raise InstallationError(f"Unknown installation location: {options.location}")

        # Clear caches to reflect new installation state
        self.config_manager.clear_cache()

    def update(self, project_only: bool = False) -> None:
        """Update existing AgentOS installations.

        Updates installed AgentOS components to the latest version,
        handling both base and project installations as specified.

        Args:
            project_only: If True, only update project installation

        Raises:
            InstallationError: If update fails or no installation found

        Example:
            >>> installer = Installer()
            >>> installer.update(project_only=False)  # Update both base and project
            >>> installer.update(project_only=True)   # Update project only
        """
        status = self.config_manager.get_install_status()

        if project_only:
            if not status.project_installed:
                raise InstallationError(
                    "No project installation found to update. "
                    "Run 'agentos install --project' to install project components first."
                )
            self._update_project(status)
        else:
            if not status.base_installed and not status.project_installed:
                raise InstallationError(
                    "No AgentOS installation found to update. Run 'agentos install' to install AgentOS first."
                )

            if status.base_installed:
                self._update_base(status)

            if status.project_installed:
                self._update_project(status)

        # Clear caches to reflect updated state
        self.config_manager.clear_cache()

    def uninstall(self, project_only: bool = False) -> None:
        """Remove AgentOS installations.

        Removes AgentOS components from the system, handling both base
        and project installations as specified.

        Args:
            project_only: If True, only remove project installation

        Raises:
            InstallationError: If uninstall fails

        Example:
            >>> installer = Installer()
            >>> installer.uninstall(project_only=True)   # Remove project only
            >>> installer.uninstall(project_only=False)  # Remove everything
        """
        status = self.config_manager.get_install_status()

        if project_only:
            if not status.project_installed:
                self.console.print("⚠️ [yellow]No project installation found to remove[/yellow]")
                return
            self._uninstall_project(status)
        else:
            removed_anything = False

            if status.project_installed:
                self._uninstall_project(status)
                removed_anything = True

            if status.base_installed:
                self._uninstall_base(status)
                removed_anything = True

            if not removed_anything:
                self.console.print("⚠️ [yellow]No AgentOS installation found to remove[/yellow]")
                return

        # Clear caches to reflect removal
        self.config_manager.clear_cache()

    def get_latest_version(self) -> str:
        """Get latest AgentOS version from GitHub API.

        Queries the GitHub API to determine the latest available version
        of AgentOS for update checking purposes.

        Returns:
            Latest version string (e.g., "1.4.3")

        Raises:
            InstallationError: If GitHub API request fails

        Example:
            >>> installer = Installer()
            >>> try:
            ...     latest = installer.get_latest_version()
            ...     print(f"Latest version: {latest}")
            ... except InstallationError as e:
            ...     print(f"Failed to check version: {e}")
        """
        try:
            # GitHub API endpoint for latest release
            url = "https://api.github.com/repos/buildermethods/agent-os/releases/latest"

            response = requests.get(url, timeout=10)
            response.raise_for_status()

            release_data = response.json()
            tag_name = release_data.get("tag_name", "")

            # Remove 'v' prefix if present
            if tag_name.startswith("v"):
                tag_name = tag_name[1:]

            if not tag_name:
                raise InstallationError("Invalid release tag from GitHub API")

            return str(tag_name)

        except requests.RequestException as e:
            raise InstallationError(f"Failed to check latest version from GitHub: {e}") from e
        except json.JSONDecodeError as e:
            raise InstallationError(f"Invalid JSON response from GitHub API: {e}") from e
        except KeyError as e:
            raise InstallationError(f"Unexpected response format from GitHub API: {e}") from e

    def _install_base(self, options: InstallOptions) -> None:
        """Install base AgentOS components.

        Args:
            options: Installation configuration options
        """
        self.console.print("🚀 [bold blue]Installing AgentOS base components...[/bold blue]")

        # Check if base already installed
        status = self.config_manager.get_install_status()
        if status.base_installed and not options.overwrite_config:
            self.console.print("⚠️ [yellow]Base installation already exists[/yellow]")
            if not self.console.input("Proceed with reinstall? [y/N]: ").lower().startswith("y"):
                return

        try:
            self.shell_executor.run_base_install(
                claude_code=options.claude_code,
                cursor=options.cursor,
                project_type=options.project_type or "default",
                overwrite_instructions=options.overwrite_instructions,
                overwrite_standards=options.overwrite_standards,
                overwrite_config=options.overwrite_config,
            )
        except Exception as e:
            raise InstallationError(f"Base installation failed: {e}") from e

    def _install_project(self, options: InstallOptions) -> None:
        """Install project-level AgentOS components.

        Args:
            options: Installation configuration options
        """
        self.console.print("📁 [bold green]Installing AgentOS project components...[/bold green]")

        # Check if base installation exists (required for project install)
        status = self.config_manager.get_install_status()
        if not status.base_installed and not options.no_base:
            raise InstallationError(
                "Base AgentOS installation required for project installation. "
                "Run 'agentos install' first, or use --no-base to skip this requirement."
            )

        # Check if project already installed
        if status.project_installed and not options.overwrite_config:
            self.console.print("⚠️ [yellow]Project installation already exists[/yellow]")
            if not self.console.input("Proceed with reinstall? [y/N]: ").lower().startswith("y"):
                return

        try:
            self.shell_executor.run_project_install(
                claude_code=options.claude_code,
                cursor=options.cursor,
                project_type=options.project_type or "default",
                overwrite_instructions=options.overwrite_instructions,
                overwrite_standards=options.overwrite_standards,
                overwrite_config=options.overwrite_config,
            )
        except Exception as e:
            raise InstallationError(f"Project installation failed: {e}") from e

    def _update_base(self, status: Any) -> None:
        """Update base installation.

        Args:
            status: Current installation status
        """
        self.console.print("🔄 [bold blue]Updating base AgentOS installation...[/bold blue]")

        try:
            # Get current and latest versions
            current_version = status.base_version or "unknown"
            try:
                latest_version = self.get_latest_version()
                if current_version == latest_version:
                    self.console.print(f"✅ Base installation is already up to date (v{current_version})")
                    return
                else:
                    self.console.print(f"📦 Updating from v{current_version} to v{latest_version}")
            except InstallationError:
                self.console.print("⚠️ [yellow]Could not check latest version, proceeding with update[/yellow]")

            # Run update by reinstalling base (this is what the bash scripts do)
            self.shell_executor.run_base_install(
                claude_code=True,  # Preserve existing integrations
                cursor=True,
                project_type="default",
                overwrite_instructions=True,
                overwrite_standards=True,
                overwrite_config=True,
            )

        except Exception as e:
            raise InstallationError(f"Base update failed: {e}") from e

    def _update_project(self, status: Any) -> None:
        """Update project installation.

        Args:
            status: Current installation status
        """
        self.console.print("🔄 [bold green]Updating project AgentOS installation...[/bold green]")

        try:
            # Determine current project configuration
            claude_code = any(agent.value == "claude_code" for agent in status.project_agents)
            cursor = any(agent.value == "cursor" for agent in status.project_agents)
            project_type = status.project_type or "default"

            self.shell_executor.run_project_install(
                claude_code=claude_code,
                cursor=cursor,
                project_type=project_type,
                overwrite_instructions=True,
                overwrite_standards=True,
                overwrite_config=True,
            )

        except Exception as e:
            raise InstallationError(f"Project update failed: {e}") from e

    def _uninstall_base(self, status: Any) -> None:
        """Remove base installation.

        Args:
            status: Current installation status
        """
        self.console.print("🗑️ [bold red]Removing base AgentOS installation...[/bold red]")

        try:
            if status.base_path and status.base_path.exists():
                # Confirm removal
                if (
                    not self.console.input(f"Remove base installation at {status.base_path}? [y/N]: ")
                    .lower()
                    .startswith("y")
                ):
                    return

                shutil.rmtree(status.base_path)
                self.console.print("✅ Base installation removed successfully")
            else:
                self.console.print("⚠️ [yellow]Base installation directory not found[/yellow]")

        except Exception as e:
            raise InstallationError(f"Base uninstall failed: {e}") from e

    def _uninstall_project(self, status: Any) -> None:
        """Remove project installation.

        Args:
            status: Current installation status
        """
        self.console.print("🗑️ [bold yellow]Removing project AgentOS installation...[/bold yellow]")

        try:
            if status.project_path and status.project_path.exists():
                # Confirm removal
                if (
                    not self.console.input(f"Remove project installation at {status.project_path}? [y/N]: ")
                    .lower()
                    .startswith("y")
                ):
                    return

                shutil.rmtree(status.project_path)
                self.console.print("✅ Project installation removed successfully")
            else:
                self.console.print("⚠️ [yellow]Project installation directory not found[/yellow]")

        except Exception as e:
            raise InstallationError(f"Project uninstall failed: {e}") from e
