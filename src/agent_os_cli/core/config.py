"""Configuration management for AgentOS.

This module provides centralized configuration management for AgentOS installations,
including base and project-level configuration discovery, validation, and caching.

The ConfigManager class handles:
- Discovery of existing AgentOS installations
- YAML configuration parsing and validation
- Project type detection and validation
- Installation status tracking
- Configuration caching for performance

Example:
    >>> from agent_os_cli.core.config import ConfigManager
    >>> config_manager = ConfigManager()
    >>> status = config_manager.get_install_status()
    >>> print(f"Base installed: {status.base_installed}")
"""

from __future__ import annotations

import json
from pathlib import Path

import yaml
from pydantic import ValidationError

from ..settings import DETECTION, PATHS
from ..types import (
    AgentOSConfig,
    AgentType,
    ConfigurationError,
    InstallStatus,
)


class ConfigManager:
    """Manages AgentOS configuration discovery and validation.

    The ConfigManager provides a centralized interface for discovering,
    loading, and validating AgentOS configurations across both base
    and project installations.

    Attributes:
        _base_config_cache: Cached base configuration to avoid repeated I/O
        _status_cache: Cached installation status for performance

    Example:
        >>> config_manager = ConfigManager()
        >>> if config_manager.get_install_status().base_installed:
        ...     config = config_manager.get_base_config()
        ...     print(f"Version: {config.agent_os_version}")
    """

    def __init__(self) -> None:
        """Initialize the configuration manager with empty caches."""
        self._base_config_cache: AgentOSConfig | None = None
        self._status_cache: InstallStatus | None = None

    def get_base_config(self) -> AgentOSConfig:
        """Load and validate base AgentOS configuration.

        Discovers the base AgentOS installation configuration, typically
        located at ~/.agent-os/config.yml, and validates it against the
        AgentOSConfig model. Results are cached for subsequent calls.

        Returns:
            AgentOSConfig: Validated base configuration object

        Raises:
            ConfigurationError: If config file not found, invalid, or fails validation

        Example:
            >>> config_manager = ConfigManager()
            >>> try:
            ...     config = config_manager.get_base_config()
            ...     print(f"AgentOS v{config.agent_os_version}")
            ... except ConfigurationError as e:
            ...     print(f"Configuration error: {e}")
        """
        if self._base_config_cache is not None:
            return self._base_config_cache

        config_path = PATHS.base_config_file_path

        if not config_path.exists():
            raise ConfigurationError(
                f"Base AgentOS configuration not found at {config_path}. "
                "Run 'agentos install' to set up base installation."
            )

        try:
            with config_path.open("r", encoding="utf-8") as f:
                config_data = yaml.safe_load(f)

            if not isinstance(config_data, dict):
                raise ConfigurationError(f"Invalid configuration format in {config_path}. Expected YAML dictionary.")

            # Validate and parse using Pydantic
            self._base_config_cache = AgentOSConfig(**config_data)
            return self._base_config_cache

        except yaml.YAMLError as e:
            raise ConfigurationError(f"Invalid YAML in configuration file {config_path}: {e}") from e
        except ValidationError as e:
            raise ConfigurationError(f"Configuration validation failed for {config_path}: {e}") from e
        except OSError as e:
            raise ConfigurationError(f"Failed to read configuration file {config_path}: {e}") from e

    def get_install_status(self) -> InstallStatus:
        """Determine current AgentOS installation status.

        Scans the system to determine what AgentOS components are currently
        installed, including base installation, project installation, and
        configured agents. Results are cached for performance.

        Returns:
            InstallStatus: Complete installation status information

        Example:
            >>> config_manager = ConfigManager()
            >>> status = config_manager.get_install_status()
            >>> if status.base_installed:
            ...     print(f"Base installation at {status.base_path}")
            >>> if status.project_installed:
            ...     print(f"Project agents: {status.project_agents}")
        """
        if self._status_cache is not None:
            return self._status_cache

        # Check for base installation
        base_path = PATHS.base_config_path
        base_installed = base_path.exists() and PATHS.base_config_file_path.exists()
        base_version = None

        if base_installed:
            try:
                config = self.get_base_config()
                base_version = config.agent_os_version
            except ConfigurationError:
                # Base path exists but config is invalid
                base_installed = False

        # Check for project installation
        project_path = PATHS.project_config_path
        project_installed = project_path.exists()
        project_agents: list[AgentType] = []
        project_type = None

        if project_installed:
            project_agents = self._detect_project_agents()
            project_type = self._detect_project_type(Path.cwd())

        self._status_cache = InstallStatus(
            base_installed=base_installed,
            base_path=base_path if base_installed else None,
            base_version=base_version,
            project_installed=project_installed,
            project_path=project_path if project_installed else None,
            project_agents=project_agents,
            project_type=project_type,
        )

        return self._status_cache

    def _detect_project_agents(self, project_path: Path | None = None) -> list[AgentType]:
        """Detect which agents are configured for a project.

        Args:
            project_path: Path to project .agent-os directory. If None, uses current project path from settings.

        Returns:
            List of configured agent types
        """
        agents: list[AgentType] = []

        if project_path is None:
            # Use settings paths
            claude_path = PATHS.claude_instructions_path
            cursor_legacy_path = PATHS.cursor_legacy_path
            cursor_rules_path = PATHS.cursor_rules_path
        else:
            # Use provided path
            claude_path = project_path / PATHS.claude_instructions_file
            cursor_legacy_path = project_path / PATHS.cursor_legacy_file
            cursor_rules_path = project_path / PATHS.cursor_rules_dir / PATHS.cursor_rules_dir_name

        # Check for Claude Code integration
        if claude_path.exists():
            agents.append(AgentType.CLAUDE_CODE)

        # Check for Cursor integration (both legacy .cursorrules and current .cursor/rules directory)
        if cursor_legacy_path.exists() or (cursor_rules_path.exists() and cursor_rules_path.is_dir()):
            agents.append(AgentType.CURSOR)

        return agents

    def _detect_project_type(self, project_root: Path) -> str | None:
        """Detect the type of the current project.

        Analyzes project files to determine the project type, which is used
        to apply appropriate development standards and instructions.

        Args:
            project_root: Path to project root directory

        Returns:
            Detected project type string, or None if cannot determine

        Example:
            >>> config_manager = ConfigManager()
            >>> project_type = config_manager._detect_project_type(Path.cwd())
            >>> print(f"Detected project type: {project_type}")
        """
        # Try each detector in order of priority
        detectors = [
            self._detect_python_project,
            self._detect_javascript_project,
            self._detect_rust_project,
            self._detect_go_project,
            self._detect_java_project,
            self._detect_cpp_project,
            self._detect_web_project,
        ]

        for detector in detectors:
            project_type = detector(project_root)
            if project_type:
                return project_type

        # Default fallback
        return "default"

    def _detect_python_project(self, project_root: Path) -> str | None:
        """Detect Python project type."""
        if not any((project_root / f).exists() for f in DETECTION.python_files):
            return None

        # Check for specific Python project types
        for file_name, project_type in DETECTION.python_project_types.items():
            if file_name != "default" and (project_root / file_name).exists():
                return project_type
        return DETECTION.python_project_types["default"]

    def _detect_javascript_project(self, project_root: Path) -> str | None:
        """Detect JavaScript/Node.js project type."""
        if not any((project_root / f).exists() for f in DETECTION.javascript_files):
            return None

        # Check for specific frameworks via package.json
        package_json = project_root / "package.json"
        if package_json.exists():
            try:
                with package_json.open("r", encoding="utf-8") as f:
                    pkg_data = json.load(f)

                deps = {**pkg_data.get("dependencies", {}), **pkg_data.get("devDependencies", {})}

                # Check for framework-specific dependencies
                for dep, project_type in DETECTION.javascript_frameworks.items():
                    if dep in deps:
                        return project_type
            except (json.JSONDecodeError, OSError):
                pass

        return "javascript"

    def _detect_rust_project(self, project_root: Path) -> str | None:
        """Detect Rust project."""
        if any((project_root / f).exists() for f in DETECTION.rust_files):
            return "rust"
        return None

    def _detect_go_project(self, project_root: Path) -> str | None:
        """Detect Go project."""
        if any((project_root / f).exists() for f in DETECTION.go_files):
            return "go"
        return None

    def _detect_java_project(self, project_root: Path) -> str | None:
        """Detect Java project type (Maven or Gradle)."""
        if any((project_root / f).exists() for f in DETECTION.java_maven_files):
            return "java-maven"
        elif any((project_root / f).exists() for f in DETECTION.java_gradle_files):
            return "java-gradle"
        return None

    def _detect_cpp_project(self, project_root: Path) -> str | None:
        """Detect C/C++ project."""
        if any((project_root / f).exists() for f in DETECTION.cpp_files):
            return "cpp"
        return None

    def _detect_web_project(self, project_root: Path) -> str | None:
        """Detect web project."""
        web_files = ["index.html", "index.htm", "webpack.config.js", "vite.config.js"]
        if any((project_root / f).exists() for f in web_files):
            return "web"
        return None

    def clear_cache(self) -> None:
        """Clear all cached configuration data.

        Forces the next calls to configuration methods to reload from disk.
        Useful when configuration files may have changed externally.

        Example:
            >>> config_manager = ConfigManager()
            >>> config_manager.clear_cache()  # Force reload on next access
        """
        self._base_config_cache = None
        self._status_cache = None
