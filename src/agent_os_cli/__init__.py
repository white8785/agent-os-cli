"""AgentOS - Spec-driven agentic development system.

AgentOS is a comprehensive CLI tool that provides centralized management
for AI-powered development environments. It enables developers to:

- Install and configure AI agents (Claude Code, Cursor, etc.)
- Manage project-specific development standards and instructions
- Maintain consistent development workflows across teams
- Integrate with existing bash-based toolchains

This package provides a modern Python CLI interface while maintaining
full backward compatibility with existing AgentOS bash scripts.

Example:
    Basic usage of the AgentOS CLI:

    >>> from agent_os_cli import InstallOptions, InstallLocation, AgentType
    >>> options = InstallOptions(
    ...     location=InstallLocation.PROJECT,
    ...     claude_code=True,
    ...     project_type="python"
    ... )
    >>> print(f"Installing to {options.location.value}")
    Installing to project

For more information, see the AgentOS documentation.
"""

# Import metadata from settings
from .settings import METADATA

__version__ = METADATA.version
__author__ = METADATA.author
__email__ = METADATA.email

# Export commonly used types
from .types import (
    AgentConfig,
    AgentOSConfig,
    AgentOSError,
    AgentType,
    ConfigurationError,
    InstallationError,
    InstallLocation,
    InstallOptions,
    InstallStatus,
    ProjectTypeConfig,
)

__all__ = [
    "AgentConfig",
    "AgentOSConfig",
    "AgentOSError",
    "AgentType",
    "ConfigurationError",
    "InstallLocation",
    "InstallOptions",
    "InstallStatus",
    "InstallationError",
    "ProjectTypeConfig",
    "__version__",
]
