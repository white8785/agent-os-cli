"""Core type definitions for AgentOS CLI.

This module provides all the type definitions used throughout the AgentOS
system, leveraging Pydantic for validation and type safety. These types
form the foundation for:

- Agent configuration and management
- Installation and deployment options
- System status tracking and validation
- Security-hardened input validation
- Enterprise-grade error handling

All models use modern Python 3.10+ type annotations and provide
comprehensive validation with detailed error messages.

Example:
    >>> from agentos.types import InstallOptions, InstallLocation
    >>> options = InstallOptions(
    ...     location=InstallLocation.BASE,
    ...     project_type="python-web"
    ... )
    >>> print(options.location.value)
    base
"""

from __future__ import annotations

from enum import Enum
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field, field_validator

from .utils.validation import validate_project_type as validate_project_type_string


class AgentType(str, Enum):
    """Supported agent types in AgentOS.

    Each agent type represents a different AI-powered development environment
    that can be integrated with AgentOS for enhanced development workflows.

    Attributes:
        CLAUDE_CODE: Anthropic's Claude Code agent integration
        CURSOR: Cursor AI editor integration

    Example:
        >>> agent = AgentType.CLAUDE_CODE
        >>> print(f"Setting up {agent.value} integration")
        Setting up claude_code integration
    """

    CLAUDE_CODE = "claude_code"
    CURSOR = "cursor"


class InstallLocation(str, Enum):
    """Installation location options for AgentOS deployment.

    Defines where AgentOS components should be installed, supporting
    both system-wide and project-specific installations.

    Attributes:
        BASE: System-wide installation in user's home directory (~/.agent-os/)
        PROJECT: Project-specific installation in current directory (./.agent-os/)

    Example:
        >>> location = InstallLocation.PROJECT
        >>> print(f"Installing to {location.value} location")
        Installing to project location
    """

    BASE = "base"  # ~/.agent-os/
    PROJECT = "project"  # ./.agent-os/


class AgentConfig(BaseModel):
    """Configuration for individual AI agents.

    Stores the configuration state and additional settings for each
    agent type integrated with AgentOS.

    Attributes:
        enabled: Whether this agent is currently active
        additional_config: Optional dictionary of agent-specific settings

    Example:
        >>> config = AgentConfig(
        ...     enabled=True,
        ...     additional_config={"api_key": "secret", "model": "claude-3"}
        ... )
        >>> print(f"Agent enabled: {config.enabled}")
        Agent enabled: True
    """

    enabled: bool
    additional_config: dict[str, str] | None = None


class ProjectTypeConfig(BaseModel):
    """Configuration for project types and templates.

    Defines the instructions and standards that should be applied
    to projects of a specific type (e.g., 'python', 'javascript', 'rust').

    Attributes:
        instructions: Project-specific instructions for development
        standards: Coding standards and best practices for this project type

    Example:
        >>> config = ProjectTypeConfig(
        ...     instructions="Use FastAPI for REST APIs",
        ...     standards="Follow PEP 8 and use type hints"
        ... )
        >>> print(config.instructions)
        Use FastAPI for REST APIs
    """

    instructions: str
    standards: str


class AgentOSConfig(BaseModel):
    """Main AgentOS configuration model.

    The root configuration object that contains all AgentOS settings,
    including agent configurations, project type definitions, and
    system-wide preferences.

    Attributes:
        agent_os_version: Version of AgentOS installation
        agents: Dictionary of agent configurations keyed by agent type
        project_types: Dictionary of project type configurations
        default_project_type: Default project type to use when none specified

    Example:
        >>> config = AgentOSConfig(
        ...     agent_os_version="1.4.2",
        ...     agents={AgentType.CLAUDE_CODE: AgentConfig(enabled=True)},
        ...     project_types={"python": ProjectTypeConfig(
        ...         instructions="Use pytest",
        ...         standards="PEP 8"
        ...     )}
        ... )
        >>> print(config.agent_os_version)
        1.4.2
    """

    agent_os_version: str
    agents: dict[AgentType, AgentConfig]
    project_types: dict[str, ProjectTypeConfig]
    default_project_type: str = "default"

    @field_validator("default_project_type")
    @classmethod
    def validate_default_project_type(cls, v: str, info: Any) -> str:
        """Ensure default project type exists in project_types."""
        if "project_types" in info.data and v not in info.data["project_types"]:
            raise ValueError(f"Default project type '{v}' not found in project_types")
        return v


class InstallOptions(BaseModel):
    """Options for AgentOS installation operations.

    Comprehensive configuration for controlling how AgentOS is installed,
    including location, agent integrations, and behavior options.

    Attributes:
        location: Where to install AgentOS (base or project)
        overwrite_instructions: Whether to overwrite existing instruction files
        overwrite_standards: Whether to overwrite existing standards files
        overwrite_config: Whether to overwrite existing config files
        claude_code: Whether to enable Claude Code integration
        cursor: Whether to enable Cursor integration
        project_type: Type of project for customized setup
        no_base: Skip base installation dependencies

    Example:
        >>> options = InstallOptions(
        ...     location=InstallLocation.PROJECT,
        ...     claude_code=True,
        ...     project_type="python-web"
        ... )
        >>> print(f"Installing to {options.location.value}")
        Installing to project
    """

    location: InstallLocation
    overwrite_instructions: bool = False
    overwrite_standards: bool = False
    overwrite_config: bool = False
    claude_code: bool = False
    cursor: bool = False
    project_type: str | None = Field(default="default", min_length=1)
    no_base: bool = False

    @field_validator("project_type")
    @classmethod
    def validate_project_type(cls, v: str | None) -> str | None:
        """Ensure project type contains only safe ASCII characters."""
        if v:
            try:
                validate_project_type_string(v)
            except ValueError:
                raise
        return v


class InstallStatus(BaseModel):
    """Current status of AgentOS installations.

    Comprehensive status information about both base and project-level
    AgentOS installations, including versions, paths, and agent configurations.

    Attributes:
        base_installed: Whether base AgentOS is installed
        base_path: Path to base installation directory
        base_version: Version of installed base AgentOS
        project_installed: Whether project-level AgentOS is installed
        project_path: Path to project installation directory
        project_agents: List of agents configured for this project
        project_type: Type of current project

    Example:
        >>> from pathlib import Path
        >>> status = InstallStatus(
        ...     base_installed=True,
        ...     base_path=Path.home() / ".agent-os",
        ...     base_version="1.4.2",
        ...     project_installed=True,
        ...     project_agents=[AgentType.CLAUDE_CODE]
        ... )
        >>> print(f"Base version: {status.base_version}")
        Base version: 1.4.2
    """

    base_installed: bool
    base_path: Path | None = None
    base_version: str | None = None
    project_installed: bool
    project_path: Path | None = None
    project_agents: list[AgentType] = Field(default_factory=list)
    project_type: str | None = None


# Custom exceptions
class AgentOSError(Exception):
    """Base exception for all AgentOS-related errors.

    This is the root exception class that all other AgentOS exceptions
    inherit from. It provides a common base for error handling and
    allows catching all AgentOS-related errors with a single except clause.

    Example:
        >>> try:
        ...     # Some AgentOS operation
        ...     pass
        ... except AgentOSError as e:
        ...     print(f"AgentOS error: {e}")
    """

    pass


class InstallationError(AgentOSError):
    """Raised when AgentOS installation operations fail.

    This exception is raised for any failure during installation,
    update, or uninstallation operations. It inherits from AgentOSError
    to provide consistent error handling.

    Example:
        >>> try:
        ...     installer.install(options)
        ... except InstallationError as e:
        ...     print(f"Installation failed: {e}")
    """

    pass


class ConfigurationError(AgentOSError):
    """Raised when AgentOS configuration is invalid or corrupted.

    This exception is raised when configuration files cannot be parsed,
    contain invalid data, or fail validation. It inherits from AgentOSError
    to provide consistent error handling.

    Example:
        >>> try:
        ...     config = config_manager.get_base_config()
        ... except ConfigurationError as e:
        ...     print(f"Configuration error: {e}")
    """

    pass
