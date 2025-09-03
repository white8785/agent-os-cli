"""Tests for AgentOS CLI interface."""

import os
import re
from unittest.mock import patch

from typer.testing import CliRunner

from agentos import __version__
from agentos.cli import app
from agentos.types import AgentType, InstallationError, InstallStatus


def strip_ansi_codes(text: str) -> str:
    """Strip ANSI escape codes from text for consistent testing."""
    return re.sub(r"\x1b\[[0-9;]*m", "", text)


class TestCLI:
    """Test CLI command functionality."""

    def setup_method(self) -> None:
        """Set up test environment."""
        # Set environment variables to force consistent terminal output
        os.environ["COLUMNS"] = "120"
        os.environ["LINES"] = "40"
        os.environ["TERM"] = "xterm-256color"
        # Disable Rich formatting for consistent test output
        os.environ["NO_COLOR"] = "1"
        os.environ["FORCE_COLOR"] = "0"
        self.runner = CliRunner()

    def test_cli_help(self) -> None:
        """Test CLI help output."""
        result = self.runner.invoke(app, ["--help"])
        assert result.exit_code == 0
        assert "AgentOS - Spec-driven agentic development system" in result.output
        assert "Commands" in result.output
        assert "version" in result.output
        assert "install" in result.output
        assert "update" in result.output
        assert "uninstall" in result.output

    def test_version_command(self) -> None:
        """Test version command output."""
        # Mock the config manager to avoid actual file system access
        mock_status = InstallStatus(base_installed=False, project_installed=False)

        with patch("agentos.cli.config_manager") as mock_config:
            mock_config.get_install_status.return_value = mock_status

            result = self.runner.invoke(app, ["version"])
            assert result.exit_code == 0
            assert "AgentOS CLI" in result.output
            assert "v1.4.3" in result.output
            assert "Phase 2 Complete" in result.output

    def test_install_help(self) -> None:
        """Test install command help."""
        result = self.runner.invoke(app, ["install", "--help"])
        assert result.exit_code == 0
        clean_output = strip_ansi_codes(result.output)
        assert "Install AgentOS base installation" in clean_output
        assert "--project" in clean_output
        assert "--claude-code" in clean_output
        assert "--cursor" in clean_output
        assert "--project-type" in clean_output
        assert "Examples:" in clean_output

    def test_install_command_basic(self) -> None:
        """Test basic install command with mocked installer."""
        with patch("agentos.cli.installer") as mock_installer:
            # Mock successful installation
            result = self.runner.invoke(app, ["install"], input="n\n")
            assert result.exit_code == 0
            mock_installer.install.assert_called()

    def test_install_command_with_options(self) -> None:
        """Test install command with various options."""
        with patch("agentos.cli.installer") as mock_installer:
            result = self.runner.invoke(
                app, ["install", "--project", "--claude-code", "--project-type", "python", "--overwrite-instructions"]
            )
            assert result.exit_code == 0
            mock_installer.install.assert_called()

            # Verify the install options were correct
            call_args = mock_installer.install.call_args[0][0]
            assert call_args.claude_code is True
            assert call_args.project_type == "python"
            assert call_args.overwrite_instructions is True

    def test_update_help(self) -> None:
        """Test update command help."""
        result = self.runner.invoke(app, ["update", "--help"])
        assert result.exit_code == 0
        clean_output = strip_ansi_codes(result.output)
        assert "Update existing AgentOS installations" in clean_output
        assert "--project" in clean_output

    def test_update_command(self) -> None:
        """Test update command."""
        with patch("agentos.cli.installer") as mock_installer:
            result = self.runner.invoke(app, ["update"])
            assert result.exit_code == 0
            mock_installer.update.assert_called_with(project_only=False)

    def test_update_command_project_only(self) -> None:
        """Test update command with project flag."""
        with patch("agentos.cli.installer") as mock_installer:
            result = self.runner.invoke(app, ["update", "--project"])
            assert result.exit_code == 0
            mock_installer.update.assert_called_with(project_only=True)

    def test_uninstall_help(self) -> None:
        """Test uninstall command help."""
        result = self.runner.invoke(app, ["uninstall", "--help"])
        assert result.exit_code == 0
        clean_output = strip_ansi_codes(result.output)
        assert "Remove AgentOS installations" in clean_output
        assert "--project" in clean_output

    def test_uninstall_command(self) -> None:
        """Test uninstall command."""
        with patch("agentos.cli.installer") as mock_installer:
            result = self.runner.invoke(app, ["uninstall"])
            assert result.exit_code == 0
            mock_installer.uninstall.assert_called_with(project_only=False)

    def test_uninstall_command_project_only(self) -> None:
        """Test uninstall command with project flag."""
        with patch("agentos.cli.installer") as mock_installer:
            result = self.runner.invoke(app, ["uninstall", "--project"])
            assert result.exit_code == 0
            mock_installer.uninstall.assert_called_with(project_only=True)

    def test_invalid_command(self) -> None:
        """Test handling of invalid commands."""
        result = self.runner.invoke(app, ["nonexistent"])
        assert result.exit_code != 0
        assert "No such command" in result.output


class TestCLIIntegration:
    """Integration tests for CLI functionality."""

    def setup_method(self) -> None:
        """Set up test environment."""
        # Set environment variables to force consistent terminal output
        os.environ["COLUMNS"] = "120"
        os.environ["LINES"] = "40"
        os.environ["TERM"] = "xterm-256color"
        # Disable Rich formatting for consistent test output
        os.environ["NO_COLOR"] = "1"
        os.environ["FORCE_COLOR"] = "0"
        self.runner = CliRunner()

    def test_cli_version_consistency(self) -> None:
        """Test that CLI version matches package version."""
        with patch("agentos.cli.config_manager") as mock_config:
            mock_config.get_install_status.return_value = InstallStatus(base_installed=False, project_installed=False)

            result = self.runner.invoke(app, ["version"])
            assert result.exit_code == 0
            assert f"v{__version__}" in result.output

    def test_help_consistency(self) -> None:
        """Test that help text is consistent across commands."""
        # Test main help
        main_help = self.runner.invoke(app, ["--help"])
        assert main_help.exit_code == 0

        # Test command helps
        commands = ["install", "update", "uninstall"]
        for cmd in commands:
            result = self.runner.invoke(app, [cmd, "--help"])
            assert result.exit_code == 0
            assert "AgentOS" in result.output or cmd in result.output

    def test_error_handling(self) -> None:
        """Test CLI error handling."""
        # Test with invalid option
        result = self.runner.invoke(app, ["install", "--invalid-option"])
        assert result.exit_code != 0

    def test_install_project_prompt_yes(self) -> None:
        """Test install base with project prompt answered yes."""
        with patch("agentos.cli.installer") as mock_installer:
            result = self.runner.invoke(app, ["install"], input="y\n")
            assert result.exit_code == 0
            # Should call install twice: once for base, once for project
            assert mock_installer.install.call_count == 2

    def test_install_project_prompt_no(self) -> None:
        """Test install base with project prompt answered no."""
        with patch("agentos.cli.installer") as mock_installer:
            result = self.runner.invoke(app, ["install"], input="n\n")
            assert result.exit_code == 0
            # Should call install once for base only
            assert mock_installer.install.call_count == 1

    def test_install_error_handling(self) -> None:
        """Test install command error handling."""
        with patch("agentos.cli.installer") as mock_installer:
            mock_installer.install.side_effect = InstallationError("Installation failed")

            result = self.runner.invoke(app, ["install", "--project"])
            assert result.exit_code == 1
            assert "Installation failed" in result.output

    def test_update_error_handling(self) -> None:
        """Test update command error handling."""
        with patch("agentos.cli.installer") as mock_installer:
            mock_installer.update.side_effect = InstallationError("Update failed")

            result = self.runner.invoke(app, ["update"])
            assert result.exit_code == 1
            assert "Update failed" in result.output

    def test_uninstall_error_handling(self) -> None:
        """Test uninstall command error handling."""
        with patch("agentos.cli.installer") as mock_installer:
            mock_installer.uninstall.side_effect = InstallationError("Uninstall failed")

            result = self.runner.invoke(app, ["uninstall"])
            assert result.exit_code == 1
            assert "Uninstall failed" in result.output

    def test_version_with_installations(self) -> None:
        """Test version command with installations present."""
        mock_status = InstallStatus(
            base_installed=True,
            base_version="1.4.2",
            project_installed=True,
            project_agents=[AgentType.CLAUDE_CODE, AgentType.CURSOR],
            project_type="python",
        )

        with patch("agentos.cli.config_manager") as mock_config:
            mock_config.get_install_status.return_value = mock_status

            result = self.runner.invoke(app, ["version"])
            assert result.exit_code == 0
            assert "v1.4.3" in result.output
            assert "claude_code" in result.output
            assert "cursor" in result.output
            assert "python" in result.output

    def test_version_error_handling(self) -> None:
        """Test version command error handling."""
        with patch("agentos.cli.config_manager") as mock_config:
            mock_config.get_install_status.side_effect = Exception("Config error")

            result = self.runner.invoke(app, ["version"])
            assert result.exit_code == 0  # Should still show basic version info
            assert "AgentOS CLI" in result.output
