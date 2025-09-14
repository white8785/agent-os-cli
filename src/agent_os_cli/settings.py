"""AgentOS Settings and Configuration Constants.

This module centralizes all static constants, file paths, and configuration
settings used throughout the AgentOS application. It uses Pydantic for
type-safe configuration management and environment variable support.
"""

from pathlib import Path

from pydantic import BaseModel, Field


class AgentOSPaths(BaseModel):
    """File and directory path constants for AgentOS."""

    # Base directory paths
    base_dir_name: str = ".agent-os"
    project_dir_name: str = ".agent-os"

    # Configuration file names
    base_config_file: str = "config.yml"
    claude_instructions_file: str = "CLAUDE.md"
    cursor_legacy_file: str = ".cursorrules"
    cursor_rules_dir: str = ".cursor"
    cursor_rules_dir_name: str = "rules"

    # Script directories
    scripts_dir: str = "scripts"
    setup_dir: str = "setup"

    @property
    def base_config_path(self) -> Path:
        """Path to base AgentOS configuration directory."""
        return Path.home() / self.base_dir_name

    @property
    def base_config_file_path(self) -> Path:
        """Path to base AgentOS configuration file."""
        return self.base_config_path / self.base_config_file

    @property
    def project_config_path(self) -> Path:
        """Path to project AgentOS configuration directory."""
        return Path.cwd() / self.project_dir_name

    @property
    def claude_instructions_path(self) -> Path:
        """Path to Claude instructions file in project."""
        return self.project_config_path / self.claude_instructions_file

    @property
    def cursor_legacy_path(self) -> Path:
        """Path to legacy Cursor rules file."""
        return self.project_config_path / self.cursor_legacy_file

    @property
    def cursor_rules_path(self) -> Path:
        """Path to current Cursor rules directory."""
        return self.project_config_path / self.cursor_rules_dir / self.cursor_rules_dir_name

    @property
    def scripts_search_paths(self) -> list[Path]:
        """List of paths to search for installation scripts."""
        base_path = self.base_config_path
        return [
            base_path / self.scripts_dir,
            base_path / self.setup_dir,
        ]


class ProjectDetectionSettings(BaseModel):
    """Settings for project type detection."""

    # Python project indicators
    python_files: list[str] = Field(
        default=[
            "pyproject.toml",
            "setup.py",
            "setup.cfg",
            "requirements.txt",
            "Pipfile",
            "poetry.lock",
            "uv.lock",
            "__init__.py",
        ]
    )

    # JavaScript/Node.js project indicators
    javascript_files: list[str] = Field(default=["package.json", "yarn.lock", "package-lock.json", "bun.lockb"])

    # Other project type indicators
    rust_files: list[str] = Field(default=["Cargo.toml"])
    go_files: list[str] = Field(default=["go.mod", "go.sum"])
    java_maven_files: list[str] = Field(default=["pom.xml"])
    java_gradle_files: list[str] = Field(default=["build.gradle", "build.gradle.kts"])
    cpp_files: list[str] = Field(default=["CMakeLists.txt", "Makefile", "configure.ac"])

    # Framework-specific dependencies for JavaScript projects
    javascript_frameworks: dict[str, str] = Field(
        default={
            "next": "javascript-nextjs",
            "react": "javascript-react",
            "vue": "javascript-vue",
            "express": "javascript-express",
        }
    )

    # Python project type mapping
    python_project_types: dict[str, str] = Field(
        default={
            "pyproject.toml": "python-modern",
            "poetry.lock": "python-poetry",
            "uv.lock": "python-uv",
            "default": "python",
        }
    )


class AgentOSMetadata(BaseModel):
    """AgentOS metadata and version information."""

    version: str = "1.4.3"
    author: str = "Brian Casel"
    email: str = "brian@buildermethods.com"
    project_name: str = "AgentOS"
    description: str = "Spec-driven agentic development system"


class ScriptExecutionSettings(BaseModel):
    """Settings for script execution behavior."""

    script_timeout: int = Field(
        default=600, description="Default timeout for script execution in seconds (10 minutes)", ge=1, le=3600
    )


class AgentOSSettings(BaseModel):
    """Main AgentOS settings container."""

    paths: AgentOSPaths = Field(default_factory=AgentOSPaths)
    detection: ProjectDetectionSettings = Field(default_factory=ProjectDetectionSettings)
    metadata: AgentOSMetadata = Field(default_factory=AgentOSMetadata)
    execution: ScriptExecutionSettings = Field(default_factory=ScriptExecutionSettings)


# Global settings instance
settings = AgentOSSettings()

# Convenience exports for backward compatibility
PATHS = settings.paths
DETECTION = settings.detection
METADATA = settings.metadata
EXECUTION = settings.execution

# Direct exports of commonly used paths
BASE_CONFIG_PATH = PATHS.base_config_path
PROJECT_CONFIG_PATH = PATHS.project_config_path
CLAUDE_INSTRUCTIONS_FILE = PATHS.claude_instructions_file
CURSOR_LEGACY_FILE = PATHS.cursor_legacy_file
CURSOR_RULES_DIR = PATHS.cursor_rules_dir
CURSOR_RULES_DIR_NAME = PATHS.cursor_rules_dir_name

__all__ = [
    "BASE_CONFIG_PATH",
    "CLAUDE_INSTRUCTIONS_FILE",
    "CURSOR_LEGACY_FILE",
    "CURSOR_RULES_DIR",
    "CURSOR_RULES_DIR_NAME",
    "DETECTION",
    "EXECUTION",
    "METADATA",
    "PATHS",
    "PROJECT_CONFIG_PATH",
    "AgentOSMetadata",
    "AgentOSPaths",
    "AgentOSSettings",
    "ProjectDetectionSettings",
    "ScriptExecutionSettings",
    "settings",
]
