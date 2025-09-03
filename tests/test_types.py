"""Comprehensive tests for AgentOS type definitions."""

from pathlib import Path
from typing import Any

import pytest
from pydantic import ValidationError

from agentos.types import (
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


class TestAgentType:
    """Test AgentType enum."""

    def test_agent_type_values(self) -> None:
        """Test that AgentType has expected values."""
        assert AgentType.CLAUDE_CODE.value == "claude_code"
        assert AgentType.CURSOR.value == "cursor"

    def test_agent_type_members(self) -> None:
        """Test all expected members exist."""
        assert set(AgentType) == {AgentType.CLAUDE_CODE, AgentType.CURSOR}


class TestInstallLocation:
    """Test InstallLocation enum."""

    def test_install_location_values(self) -> None:
        """Test that InstallLocation has expected values."""
        assert InstallLocation.BASE.value == "base"
        assert InstallLocation.PROJECT.value == "project"

    def test_install_location_members(self) -> None:
        """Test all expected members exist."""
        assert set(InstallLocation) == {InstallLocation.BASE, InstallLocation.PROJECT}


class TestAgentConfig:
    """Test AgentConfig model."""

    def test_agent_config_creation(self) -> None:
        """Test creating AgentConfig with valid data."""
        config = AgentConfig(enabled=True)
        assert config.enabled is True
        assert config.additional_config is None

    def test_agent_config_with_additional_config(self) -> None:
        """Test AgentConfig with additional configuration."""
        additional = {"key": "value", "another": "data"}
        config = AgentConfig(enabled=False, additional_config=additional)
        assert config.enabled is False
        assert config.additional_config == additional

    def test_agent_config_validation(self) -> None:
        """Test AgentConfig validation."""
        with pytest.raises(ValidationError) as exc_info:
            AgentConfig()  # type: ignore
        assert "enabled" in str(exc_info.value)


class TestProjectTypeConfig:
    """Test ProjectTypeConfig model."""

    def test_project_type_config_creation(self) -> None:
        """Test creating ProjectTypeConfig with valid data."""
        config = ProjectTypeConfig(instructions="Some instructions", standards="Some standards")
        assert config.instructions == "Some instructions"
        assert config.standards == "Some standards"

    def test_project_type_config_validation(self) -> None:
        """Test ProjectTypeConfig validation."""
        with pytest.raises(ValidationError) as exc_info:
            ProjectTypeConfig(instructions="test")  # type: ignore
        assert "standards" in str(exc_info.value)


class TestAgentOSConfig:
    """Test AgentOSConfig model."""

    @pytest.fixture
    def valid_config_data(self) -> dict[str, Any]:
        """Provide valid configuration data."""
        return {
            "agent_os_version": "1.4.2",
            "agents": {
                AgentType.CLAUDE_CODE: AgentConfig(enabled=True),
                AgentType.CURSOR: AgentConfig(enabled=False),
            },
            "project_types": {
                "default": ProjectTypeConfig(instructions="Default instructions", standards="Default standards"),
                "python": ProjectTypeConfig(instructions="Python instructions", standards="Python standards"),
            },
            "default_project_type": "default",
        }

    def test_agent_os_config_creation(self, valid_config_data: dict[str, Any]) -> None:
        """Test creating AgentOSConfig with valid data."""
        config = AgentOSConfig(**valid_config_data)
        assert config.agent_os_version == "1.4.2"
        assert config.default_project_type == "default"
        assert len(config.agents) == 2
        assert len(config.project_types) == 2

    def test_agent_os_config_default_project_type_validation(self, valid_config_data: dict[str, Any]) -> None:
        """Test validation of default project type."""
        # Invalid default project type
        valid_config_data["default_project_type"] = "nonexistent"
        with pytest.raises(ValidationError) as exc_info:
            AgentOSConfig(**valid_config_data)
        assert "not found in project_types" in str(exc_info.value)

    def test_agent_os_config_minimal(self) -> None:
        """Test creating AgentOSConfig with minimal data."""
        config = AgentOSConfig(
            agent_os_version="1.0.0",
            agents={},
            project_types={"default": ProjectTypeConfig(instructions="inst", standards="std")},
        )
        assert config.default_project_type == "default"


class TestInstallOptions:
    """Test InstallOptions model."""

    def test_install_options_defaults(self) -> None:
        """Test InstallOptions with default values."""
        options = InstallOptions(location=InstallLocation.BASE)
        assert options.location == InstallLocation.BASE
        assert options.overwrite_instructions is False
        assert options.overwrite_standards is False
        assert options.overwrite_config is False
        assert options.claude_code is False
        assert options.cursor is False
        assert options.project_type == "default"
        assert options.no_base is False

    def test_install_options_all_set(self) -> None:
        """Test InstallOptions with all values set."""
        options = InstallOptions(
            location=InstallLocation.PROJECT,
            overwrite_instructions=True,
            overwrite_standards=True,
            overwrite_config=True,
            claude_code=True,
            cursor=True,
            project_type="python",
            no_base=True,
        )
        assert options.location == InstallLocation.PROJECT
        assert all(
            [
                options.overwrite_instructions,
                options.overwrite_standards,
                options.overwrite_config,
                options.claude_code,
                options.cursor,
                options.no_base,
            ]
        )
        assert options.project_type == "python"

    def test_install_options_project_type_validation(self) -> None:
        """Test project type validation."""
        # Valid project types
        valid_types = ["python", "node-js", "rust_project", "my-project-123"]
        for project_type in valid_types:
            options = InstallOptions(location=InstallLocation.BASE, project_type=project_type)
            assert options.project_type == project_type

        # Invalid project types
        invalid_types = ["project/type", "project@type", "project space", "../evil", "---", "___"]
        for project_type in invalid_types:
            with pytest.raises(ValidationError) as exc_info:
                InstallOptions(location=InstallLocation.BASE, project_type=project_type)
            # Different error messages for different validation failures
            error_msg = str(exc_info.value)
            assert (
                "alphanumeric characters" in error_msg
                or "Invalid project type" in error_msg
                or "cannot start or end" in error_msg
            )

    @pytest.mark.parametrize(
        "project_type",
        [
            "project/type",  # Contains slash
            "project@type",  # Contains @
            "project space",  # Contains space
            "../evil",  # Path traversal
            "---",  # Only dashes
            "___",  # Only underscores
            "",  # Empty string
            "project\ntype",  # Newline
            "project\ttype",  # Tab
            "project$type",  # Dollar sign
            "project|type",  # Pipe
            "проект",  # Non-ASCII
        ],
    )
    def test_install_options_project_type_invalid_chars(self, project_type: str) -> None:
        """Test that project types with invalid characters are rejected."""
        with pytest.raises(ValidationError):
            InstallOptions(location=InstallLocation.BASE, project_type=project_type)


class TestInstallStatus:
    """Test InstallStatus model."""

    def test_install_status_not_installed(self) -> None:
        """Test InstallStatus for no installations."""
        status = InstallStatus(
            base_installed=False,
            project_installed=False,
        )
        assert status.base_installed is False
        assert status.base_path is None
        assert status.base_version is None
        assert status.project_installed is False
        assert status.project_path is None
        assert status.project_agents == []
        assert status.project_type is None

    def test_install_status_base_only(self) -> None:
        """Test InstallStatus with base installation only."""
        status = InstallStatus(
            base_installed=True,
            base_path=Path.home() / ".agent-os",
            base_version="1.4.2",
            project_installed=False,
        )
        assert status.base_installed is True
        assert status.base_path == Path.home() / ".agent-os"
        assert status.base_version == "1.4.2"
        assert status.project_installed is False

    def test_install_status_full(self) -> None:
        """Test InstallStatus with full installation."""
        status = InstallStatus(
            base_installed=True,
            base_path=Path.home() / ".agent-os",
            base_version="1.4.2",
            project_installed=True,
            project_path=Path(".agent-os"),
            project_agents=[AgentType.CLAUDE_CODE, AgentType.CURSOR],
            project_type="python",
        )
        assert status.base_installed is True
        assert status.project_installed is True
        assert len(status.project_agents) == 2
        assert AgentType.CLAUDE_CODE in status.project_agents
        assert AgentType.CURSOR in status.project_agents
        assert status.project_type == "python"


class TestExceptions:
    """Test custom exception classes."""

    def test_agent_os_error(self) -> None:
        """Test AgentOSError base exception."""
        error = AgentOSError("Test error")
        assert str(error) == "Test error"
        assert isinstance(error, Exception)

    def test_installation_error(self) -> None:
        """Test InstallationError exception."""
        error = InstallationError("Installation failed")
        assert str(error) == "Installation failed"
        assert isinstance(error, AgentOSError)
        assert isinstance(error, Exception)

    def test_configuration_error(self) -> None:
        """Test ConfigurationError exception."""
        error = ConfigurationError("Invalid config")
        assert str(error) == "Invalid config"
        assert isinstance(error, AgentOSError)
        assert isinstance(error, Exception)

    def test_exception_hierarchy(self) -> None:
        """Test exception inheritance hierarchy."""
        # InstallationError should be caught as AgentOSError
        try:
            raise InstallationError("test")
        except AgentOSError:
            pass  # This should catch it

        # ConfigurationError should be caught as AgentOSError
        try:
            raise ConfigurationError("test")
        except AgentOSError:
            pass  # This should catch it


class TestTypeIntegration:
    """Integration tests for type interactions."""

    def test_full_config_serialization(self) -> None:
        """Test serialization/deserialization of full configuration."""
        config = AgentOSConfig(
            agent_os_version="1.4.2",
            agents={
                AgentType.CLAUDE_CODE: AgentConfig(enabled=True, additional_config={"api_key": "secret"}),
            },
            project_types={
                "default": ProjectTypeConfig(instructions="Default instructions", standards="Default standards"),
            },
        )

        # Convert to dict and back
        config_dict = config.model_dump()
        recreated = AgentOSConfig(**config_dict)

        assert recreated.agent_os_version == config.agent_os_version
        assert recreated.agents[AgentType.CLAUDE_CODE].enabled is True
        assert recreated.default_project_type == "default"

    def test_install_options_location_enum(self) -> None:
        """Test that InstallOptions properly uses InstallLocation enum."""
        # Should accept enum values
        options = InstallOptions(location=InstallLocation.BASE)
        assert options.location == InstallLocation.BASE

        # Should accept string values that match enum
        options = InstallOptions(location="project")  # type: ignore
        assert options.location == InstallLocation.PROJECT

        # Should reject invalid values
        with pytest.raises(ValidationError):
            InstallOptions(location="invalid")  # type: ignore
