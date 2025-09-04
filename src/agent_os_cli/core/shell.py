"""Shell script integration for AgentOS.

This module provides secure shell script execution capabilities for AgentOS,
maintaining backward compatibility with existing bash-based workflows while
adding enterprise-grade security and error handling.

The ShellExecutor class handles:
- Discovery of AgentOS shell scripts from multiple locations
- Secure subprocess execution with input validation
- Rich console output formatting and progress tracking
- Comprehensive error handling and timeout management
- Security-hardened command execution

Example:
    >>> from agent_os_cli.core.shell import ShellExecutor
    >>> executor = ShellExecutor()
    >>> executor.run_base_install(claude_code=True)
"""

from __future__ import annotations

import site
import subprocess
import sys
from pathlib import Path

from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn

from ..settings import EXECUTION, PATHS
from ..types import InstallationError
from ..utils.validation import validate_project_type


class ShellExecutor:
    """Executes AgentOS shell scripts with security and error handling.

    The ShellExecutor provides a secure interface for running AgentOS bash
    scripts while maintaining backward compatibility with existing workflows.
    It includes comprehensive security validation, timeout handling, and
    rich console output.

    Attributes:
        console: Rich console for formatted output
        script_timeout: Default timeout for script execution (10 minutes)

    Example:
        >>> executor = ShellExecutor()
        >>> try:
        ...     executor.run_base_install(claude_code=True, cursor=False)
        ... except InstallationError as e:
        ...     print(f"Installation failed: {e}")
    """

    def __init__(self, console: Console | None = None, script_timeout: int | None = None) -> None:
        """Initialize shell executor with console and default settings.

        Args:
            console: Optional Rich console instance for output formatting
            script_timeout: Optional timeout override in seconds (defaults to settings)
        """
        self.console = console or Console()
        self.script_timeout = script_timeout if script_timeout is not None else EXECUTION.script_timeout

    def run_base_install(
        self,
        claude_code: bool = False,
        cursor: bool = False,
        project_type: str = "default",
        overwrite_instructions: bool = False,
        overwrite_standards: bool = False,
        overwrite_config: bool = False,
    ) -> None:
        """Execute base AgentOS installation script.

        Runs the base installation script with the specified options,
        providing secure execution and comprehensive error handling.

        Args:
            claude_code: Enable Claude Code integration
            cursor: Enable Cursor integration
            project_type: Project type for customized setup
            overwrite_instructions: Overwrite existing instruction files
            overwrite_standards: Overwrite existing standards files
            overwrite_config: Overwrite existing config.yml

        Raises:
            InstallationError: If installation script fails or times out

        Example:
            >>> executor = ShellExecutor()
            >>> executor.run_base_install(
            ...     claude_code=True,
            ...     project_type="python-web"
            ... )
        """
        self._validate_project_type(project_type)

        script_path = self._find_script("base.sh")
        if not script_path:
            raise InstallationError(
                "Base installation script 'base.sh' not found. "
                "Please ensure AgentOS is properly installed or available."
            )

        # Build command arguments securely
        cmd_args = [str(script_path)]

        # Add boolean flags
        if claude_code:
            cmd_args.append("--claude-code")
        if cursor:
            cmd_args.append("--cursor")
        if overwrite_instructions:
            cmd_args.append("--overwrite-instructions")
        if overwrite_standards:
            cmd_args.append("--overwrite-standards")
        if overwrite_config:
            cmd_args.append("--overwrite-config")

        # Add project type (validated above)
        if project_type != "default":
            cmd_args.extend(["--project-type", project_type])

        self._execute_script(
            cmd_args,
            description="Installing AgentOS base components",
            success_message="✅ Base installation completed successfully",
        )

    def run_project_install(
        self,
        claude_code: bool = False,
        cursor: bool = False,
        project_type: str = "default",
        overwrite_instructions: bool = False,
        overwrite_standards: bool = False,
        overwrite_config: bool = False,
    ) -> None:
        """Execute project-level AgentOS installation script.

        Runs the project installation script with the specified options,
        installing AgentOS components to the current project directory.

        Args:
            claude_code: Enable Claude Code integration
            cursor: Enable Cursor integration
            project_type: Project type for customized setup
            overwrite_instructions: Overwrite existing instruction files
            overwrite_standards: Overwrite existing standards files
            overwrite_config: Overwrite existing config.yml

        Raises:
            InstallationError: If installation script fails or times out

        Example:
            >>> executor = ShellExecutor()
            >>> executor.run_project_install(
            ...     claude_code=True,
            ...     project_type="python"
            ... )
        """
        self._validate_project_type(project_type)

        script_path = self._find_script("project.sh")
        if not script_path:
            raise InstallationError(
                "Project installation script 'project.sh' not found. "
                "Please ensure AgentOS base installation is complete."
            )

        # Build command arguments securely
        cmd_args = [str(script_path)]

        # Add boolean flags
        if claude_code:
            cmd_args.append("--claude-code")
        if cursor:
            cmd_args.append("--cursor")
        if overwrite_instructions:
            cmd_args.append("--overwrite-instructions")
        if overwrite_standards:
            cmd_args.append("--overwrite-standards")
        if overwrite_config:
            cmd_args.append("--overwrite-config")

        # Add project type (validated above) - project.sh expects --project-type=VALUE format
        if project_type != "default":
            cmd_args.append(f"--project-type={project_type}")

        self._execute_script(
            cmd_args,
            description="Installing AgentOS project components",
            success_message="✅ Project installation completed successfully",
        )

    def _find_script(self, script_name: str) -> Path | None:
        """Find AgentOS script in multiple locations with fallbacks.

        Searches for the specified script in the following priority order:
        1. Bundled scripts in the Python package
        2. User's ~/.agent-os/ directory
        3. System-wide locations

        Args:
            script_name: Name of script file to find (e.g., "base.sh")

        Returns:
            Path to script file, or None if not found

        Example:
            >>> executor = ShellExecutor()
            >>> script_path = executor._find_script("base.sh")
            >>> if script_path:
            ...     print(f"Found script at: {script_path}")
        """
        search_locations: list[Path] = [
            # Development: scripts in source repository
            Path(__file__).parent.parent.parent.parent / "setup" / script_name,
            # Installed: data files in site-packages share location
            Path(sys.prefix) / "share" / "agent-os-cli" / "setup" / script_name,
            # User installation paths from settings
            *[path / script_name for path in PATHS.scripts_search_paths],
            # Current working directory (for development)
            Path.cwd() / "setup" / script_name,
            # System locations
            Path("/usr/local/bin") / script_name,
            Path("/usr/bin") / script_name,
        ]

        # Also check site-packages directly if available
        site_packages = site.getsitepackages() if hasattr(site, "getsitepackages") else []
        if site_packages:
            search_locations.insert(2, Path(site_packages[0]) / "share" / "agent-os-cli" / "setup" / script_name)

        for location in search_locations:
            if location.exists() and location.is_file():
                # Verify script is executable
                if not location.stat().st_mode & 0o111:
                    self.console.print(f"⚠️ [yellow]Script {location} found but not executable[/yellow]")
                    continue
                return location

        return None

    def _validate_project_type(self, project_type: str) -> None:
        """Validate project type for security.

        Ensures the project type contains only safe characters to prevent
        shell injection vulnerabilities when passed to scripts.

        Args:
            project_type: Project type string to validate

        Raises:
            InstallationError: If project type contains unsafe characters
        """
        try:
            validate_project_type(project_type)
        except ValueError as e:
            raise InstallationError(str(e)) from e

    def _execute_script(
        self,
        cmd_args: list[str],
        description: str,
        success_message: str,
    ) -> None:
        """Execute shell script with comprehensive error handling.

        Runs the specified command with security safeguards, timeout handling,
        and rich console output formatting.

        Args:
            cmd_args: List of command arguments (already validated)
            description: Description for progress display
            success_message: Message to show on successful completion

        Raises:
            InstallationError: If script execution fails or times out
        """
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=self.console,
        ) as progress:
            task = progress.add_task(description, total=None)

            try:
                # Execute with security safeguards
                # Note: cmd_args[0] is already validated as an existing executable file
                result = subprocess.run(
                    cmd_args,
                    check=False,  # We'll handle return codes manually
                    capture_output=True,
                    text=True,
                    timeout=self.script_timeout,
                    # Security: Don't use shell=True, pass args as list
                    shell=False,
                    # Prevent script from accessing sensitive environment
                    env={
                        "PATH": "/usr/local/bin:/usr/bin:/bin",
                        "HOME": str(Path.home()),
                        "USER": str(Path.home().name),
                        "LANG": "en_US.UTF-8",
                    },
                )

                progress.update(task, completed=True)

                # Handle script results
                if result.returncode == 0:
                    self.console.print(success_message)
                    if result.stdout.strip():
                        self.console.print("\n📝 [dim]Script output:[/dim]")
                        self.console.print(result.stdout.strip())
                else:
                    # Script failed
                    error_msg = f"Script failed with exit code {result.returncode}"
                    if result.stderr.strip():
                        error_msg += f"\nError output: {result.stderr.strip()}"
                    if result.stdout.strip():
                        error_msg += f"\nStandard output: {result.stdout.strip()}"

                    raise InstallationError(error_msg)

            except subprocess.TimeoutExpired as e:
                progress.update(task, completed=True)
                raise InstallationError(
                    f"Script execution timed out after {self.script_timeout} seconds. "
                    "The installation may be taking longer than expected or may have hung."
                ) from e

            except subprocess.SubprocessError as e:
                progress.update(task, completed=True)
                raise InstallationError(f"Failed to execute installation script: {e}") from e

            except Exception as e:
                progress.update(task, completed=True)
                raise InstallationError(f"Unexpected error during script execution: {e}") from e
