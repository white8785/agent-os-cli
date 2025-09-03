"""Tests for AgentOS installation logic."""

import json
from unittest.mock import Mock, patch

import pytest
import requests

from agentos.core.installer import Installer
from agentos.types import InstallationError, InstallLocation, InstallOptions


class TestInstaller:
    """Test Installer functionality."""

    def setup_method(self) -> None:
        """Set up test environment."""
        self.mock_console = Mock()
        self.mock_config_manager = Mock()
        self.mock_shell_executor = Mock()

        self.installer = Installer(
            config_manager=self.mock_config_manager,
            shell_executor=self.mock_shell_executor,
            console=self.mock_console,
        )

    def test_init_default_dependencies(self) -> None:
        """Test Installer initialization with default dependencies."""
        installer = Installer()
        assert installer.console is not None
        assert installer.config_manager is not None
        assert installer.shell_executor is not None

    def test_init_custom_dependencies(self) -> None:
        """Test Installer initialization with custom dependencies."""
        console = Mock()
        config_manager = Mock()
        shell_executor = Mock()

        installer = Installer(
            config_manager=config_manager,
            shell_executor=shell_executor,
            console=console,
        )

        assert installer.console is console
        assert installer.config_manager is config_manager
        assert installer.shell_executor is shell_executor

    def test_install_base_location(self) -> None:
        """Test installation with base location."""
        options = InstallOptions(location=InstallLocation.BASE, claude_code=True)

        with patch.object(self.installer, "_install_base") as mock_install_base:
            self.installer.install(options)

            mock_install_base.assert_called_once_with(options)
            self.mock_config_manager.clear_cache.assert_called_once()

    def test_install_project_location(self) -> None:
        """Test installation with project location."""
        options = InstallOptions(location=InstallLocation.PROJECT, cursor=True)

        with patch.object(self.installer, "_install_project") as mock_install_project:
            self.installer.install(options)

            mock_install_project.assert_called_once_with(options)
            self.mock_config_manager.clear_cache.assert_called_once()

    def test_install_invalid_location(self) -> None:
        """Test installation with invalid location."""
        # Create invalid options by bypassing validation
        options = Mock()
        options.location = "invalid_location"

        with pytest.raises(InstallationError, match="Unknown installation location"):
            self.installer.install(options)

    def test_update_project_only(self) -> None:
        """Test update with project_only=True."""
        status = Mock()
        status.project_installed = True
        status.base_installed = False
        self.mock_config_manager.get_install_status.return_value = status

        with patch.object(self.installer, "_update_project") as mock_update_project:
            self.installer.update(project_only=True)

            mock_update_project.assert_called_once_with(status)
            self.mock_config_manager.clear_cache.assert_called_once()

    def test_update_project_only_not_installed(self) -> None:
        """Test update project_only when project not installed."""
        status = Mock()
        status.project_installed = False
        self.mock_config_manager.get_install_status.return_value = status

        with pytest.raises(InstallationError, match="No project installation found to update"):
            self.installer.update(project_only=True)

    def test_update_both_installations(self) -> None:
        """Test update of both base and project installations."""
        status = Mock()
        status.base_installed = True
        status.project_installed = True
        self.mock_config_manager.get_install_status.return_value = status

        with (
            patch.object(self.installer, "_update_base") as mock_update_base,
            patch.object(self.installer, "_update_project") as mock_update_project,
        ):

            self.installer.update(project_only=False)

            mock_update_base.assert_called_once_with(status)
            mock_update_project.assert_called_once_with(status)
            self.mock_config_manager.clear_cache.assert_called_once()

    def test_update_no_installations(self) -> None:
        """Test update when no installations found."""
        status = Mock()
        status.base_installed = False
        status.project_installed = False
        self.mock_config_manager.get_install_status.return_value = status

        with pytest.raises(InstallationError, match="No AgentOS installation found to update"):
            self.installer.update(project_only=False)

    def test_uninstall_project_only(self) -> None:
        """Test uninstall with project_only=True."""
        status = Mock()
        status.project_installed = True
        self.mock_config_manager.get_install_status.return_value = status

        with patch.object(self.installer, "_uninstall_project") as mock_uninstall_project:
            self.installer.uninstall(project_only=True)

            mock_uninstall_project.assert_called_once_with(status)
            self.mock_config_manager.clear_cache.assert_called_once()

    def test_uninstall_project_only_not_installed(self) -> None:
        """Test uninstall project_only when project not installed."""
        status = Mock()
        status.project_installed = False
        self.mock_config_manager.get_install_status.return_value = status

        self.installer.uninstall(project_only=True)

        # Should print info message and not call uninstall methods
        self.mock_console.print.assert_called_with("⚠️ [yellow]No project installation found to remove[/yellow]")

    def test_uninstall_both_installations(self) -> None:
        """Test uninstall of both installations."""
        status = Mock()
        status.base_installed = True
        status.project_installed = True
        self.mock_config_manager.get_install_status.return_value = status

        with (
            patch.object(self.installer, "_uninstall_base") as mock_uninstall_base,
            patch.object(self.installer, "_uninstall_project") as mock_uninstall_project,
        ):

            self.installer.uninstall(project_only=False)

            mock_uninstall_project.assert_called_once_with(status)
            mock_uninstall_base.assert_called_once_with(status)
            self.mock_config_manager.clear_cache.assert_called_once()

    def test_uninstall_no_installations(self) -> None:
        """Test uninstall when no installations found."""
        status = Mock()
        status.base_installed = False
        status.project_installed = False
        self.mock_config_manager.get_install_status.return_value = status

        self.installer.uninstall(project_only=False)

        # Should print info message
        self.mock_console.print.assert_called_with("⚠️ [yellow]No AgentOS installation found to remove[/yellow]")

    @patch("requests.get")
    def test_get_latest_version_success(self, mock_get: Mock) -> None:
        """Test successful version retrieval from GitHub API."""
        mock_response = Mock()
        mock_response.json.return_value = {"tag_name": "v1.5.0"}
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response

        version = self.installer.get_latest_version()

        assert version == "1.5.0"
        mock_get.assert_called_once_with(
            "https://api.github.com/repos/buildermethods/agent-os/releases/latest", timeout=10
        )

    @patch("requests.get")
    def test_get_latest_version_without_v_prefix(self, mock_get: Mock) -> None:
        """Test version retrieval when tag doesn't have 'v' prefix."""
        mock_response = Mock()
        mock_response.json.return_value = {"tag_name": "1.5.0"}
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response

        version = self.installer.get_latest_version()

        assert version == "1.5.0"

    @patch("requests.get")
    def test_get_latest_version_network_error(self, mock_get: Mock) -> None:
        """Test version retrieval with network error."""
        mock_get.side_effect = requests.ConnectionError("Network error")

        with pytest.raises(InstallationError, match="Failed to check latest version from GitHub"):
            self.installer.get_latest_version()

    @patch("requests.get")
    def test_get_latest_version_http_error(self, mock_get: Mock) -> None:
        """Test version retrieval with HTTP error."""
        mock_response = Mock()
        mock_response.raise_for_status.side_effect = requests.HTTPError("404 Not Found")
        mock_get.return_value = mock_response

        with pytest.raises(InstallationError, match="Failed to check latest version from GitHub"):
            self.installer.get_latest_version()

    @patch("requests.get")
    def test_get_latest_version_invalid_json(self, mock_get: Mock) -> None:
        """Test version retrieval with invalid JSON response."""

        mock_response = Mock()
        mock_response.json.side_effect = json.JSONDecodeError("Invalid JSON", "doc", 0)
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response

        with pytest.raises(InstallationError, match="Invalid JSON response from GitHub API"):
            self.installer.get_latest_version()

    @patch("requests.get")
    def test_get_latest_version_missing_tag(self, mock_get: Mock) -> None:
        """Test version retrieval with missing tag_name."""
        mock_response = Mock()
        mock_response.json.return_value = {}  # Missing tag_name
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response

        with pytest.raises(InstallationError, match="Invalid release tag from GitHub API"):
            self.installer.get_latest_version()

    def test_install_base_success(self) -> None:
        """Test successful base installation."""
        options = InstallOptions(
            location=InstallLocation.BASE,
            claude_code=True,
            project_type="python",
            overwrite_config=True,
        )

        status = Mock()
        status.base_installed = False
        self.mock_config_manager.get_install_status.return_value = status

        self.installer._install_base(options)

        self.mock_console.print.assert_called_with("🚀 [bold blue]Installing AgentOS base components...[/bold blue]")
        self.mock_shell_executor.run_base_install.assert_called_once_with(
            claude_code=True,
            cursor=False,
            project_type="python",
            overwrite_instructions=False,
            overwrite_standards=False,
            overwrite_config=True,
        )

    def test_install_base_already_installed(self) -> None:
        """Test base installation when already installed."""
        options = InstallOptions(location=InstallLocation.BASE)

        status = Mock()
        status.base_installed = True
        self.mock_config_manager.get_install_status.return_value = status

        # Mock user declining to reinstall
        self.mock_console.input.return_value = "n"

        self.installer._install_base(options)

        # Should prompt for reinstall and return early
        self.mock_console.input.assert_called_once()
        self.mock_shell_executor.run_base_install.assert_not_called()

    def test_install_base_reinstall_confirmed(self) -> None:
        """Test base installation reinstall when confirmed."""
        options = InstallOptions(location=InstallLocation.BASE)

        status = Mock()
        status.base_installed = True
        self.mock_config_manager.get_install_status.return_value = status

        # Mock user confirming reinstall
        self.mock_console.input.return_value = "yes"

        self.installer._install_base(options)

        # Should proceed with installation
        self.mock_shell_executor.run_base_install.assert_called_once()

    def test_install_base_shell_error(self) -> None:
        """Test base installation with shell executor error."""
        options = InstallOptions(location=InstallLocation.BASE)

        status = Mock()
        status.base_installed = False
        self.mock_config_manager.get_install_status.return_value = status

        self.mock_shell_executor.run_base_install.side_effect = Exception("Shell error")

        with pytest.raises(InstallationError, match="Base installation failed"):
            self.installer._install_base(options)

    def test_install_project_success(self) -> None:
        """Test successful project installation."""
        options = InstallOptions(
            location=InstallLocation.PROJECT,
            cursor=True,
            project_type="javascript",
        )

        status = Mock()
        status.base_installed = True
        status.project_installed = False
        self.mock_config_manager.get_install_status.return_value = status

        self.installer._install_project(options)

        self.mock_console.print.assert_called_with(
            "📁 [bold green]Installing AgentOS project components...[/bold green]"
        )
        self.mock_shell_executor.run_project_install.assert_called_once_with(
            claude_code=False,
            cursor=True,
            project_type="javascript",
            overwrite_instructions=False,
            overwrite_standards=False,
            overwrite_config=False,
        )

    def test_install_project_no_base(self) -> None:
        """Test project installation without base installation."""
        options = InstallOptions(location=InstallLocation.PROJECT, no_base=False)

        status = Mock()
        status.base_installed = False
        self.mock_config_manager.get_install_status.return_value = status

        with pytest.raises(InstallationError, match="Base AgentOS installation required"):
            self.installer._install_project(options)

    def test_install_project_no_base_skip(self) -> None:
        """Test project installation skipping base requirement."""
        options = InstallOptions(location=InstallLocation.PROJECT, no_base=True)

        status = Mock()
        status.base_installed = False
        status.project_installed = False
        self.mock_config_manager.get_install_status.return_value = status

        self.installer._install_project(options)

        # Should proceed despite no base installation
        self.mock_shell_executor.run_project_install.assert_called_once()

    def test_install_project_already_installed(self) -> None:
        """Test project installation when already installed."""
        options = InstallOptions(location=InstallLocation.PROJECT)

        status = Mock()
        status.base_installed = True
        status.project_installed = True
        self.mock_config_manager.get_install_status.return_value = status

        # Mock user declining to reinstall
        self.mock_console.input.return_value = "n"

        self.installer._install_project(options)

        # Should prompt and return early
        self.mock_console.input.assert_called_once()
        self.mock_shell_executor.run_project_install.assert_not_called()

    def test_update_base_current_version(self) -> None:
        """Test base update when already current."""
        status = Mock()
        status.base_version = "1.4.2"

        with patch.object(self.installer, "get_latest_version", return_value="1.4.2"):
            self.installer._update_base(status)

            self.mock_console.print.assert_any_call("✅ Base installation is already up to date (v1.4.2)")
            self.mock_shell_executor.run_base_install.assert_not_called()

    def test_update_base_new_version(self) -> None:
        """Test base update with new version available."""
        status = Mock()
        status.base_version = "1.4.2"

        with patch.object(self.installer, "get_latest_version", return_value="1.5.0"):
            self.installer._update_base(status)

            self.mock_console.print.assert_any_call("📦 Updating from v1.4.2 to v1.5.0")
            self.mock_shell_executor.run_base_install.assert_called_once()

    def test_update_base_version_check_failed(self) -> None:
        """Test base update when version check fails."""
        status = Mock()
        status.base_version = "1.4.2"

        with patch.object(self.installer, "get_latest_version", side_effect=InstallationError("Network error")):
            self.installer._update_base(status)

            # Should proceed with update despite version check failure
            self.mock_shell_executor.run_base_install.assert_called_once()

    def test_update_project_with_agents(self) -> None:
        """Test project update preserving agent configuration."""
        status = Mock()
        status.project_agents = [Mock(value="claude_code"), Mock(value="cursor")]
        status.project_type = "python"

        self.installer._update_project(status)

        self.mock_shell_executor.run_project_install.assert_called_once_with(
            claude_code=True,
            cursor=True,
            project_type="python",
            overwrite_instructions=True,
            overwrite_standards=True,
            overwrite_config=True,
        )

    def test_uninstall_base_confirmed(self) -> None:
        """Test base uninstall when confirmed."""
        status = Mock()
        status.base_path = Mock()
        status.base_path.exists.return_value = True

        # Mock user confirming removal
        self.mock_console.input.return_value = "yes"

        with patch("shutil.rmtree") as mock_rmtree:
            self.installer._uninstall_base(status)

            mock_rmtree.assert_called_once_with(status.base_path)
            self.mock_console.print.assert_any_call("✅ Base installation removed successfully")

    def test_uninstall_base_declined(self) -> None:
        """Test base uninstall when declined."""
        status = Mock()
        status.base_path = Mock()
        status.base_path.exists.return_value = True

        # Mock user declining removal
        self.mock_console.input.return_value = "no"

        with patch("shutil.rmtree") as mock_rmtree:
            self.installer._uninstall_base(status)

            # Should not remove anything
            mock_rmtree.assert_not_called()

    def test_uninstall_base_path_not_exists(self) -> None:
        """Test base uninstall when path doesn't exist."""
        status = Mock()
        status.base_path = Mock()
        status.base_path.exists.return_value = False

        self.installer._uninstall_base(status)

        self.mock_console.print.assert_called_with("⚠️ [yellow]Base installation directory not found[/yellow]")

    def test_uninstall_project_success(self) -> None:
        """Test successful project uninstall."""
        status = Mock()
        status.project_path = Mock()
        status.project_path.exists.return_value = True

        # Mock user confirming removal
        self.mock_console.input.return_value = "y"

        with patch("shutil.rmtree") as mock_rmtree:
            self.installer._uninstall_project(status)

            mock_rmtree.assert_called_once_with(status.project_path)

    def test_uninstall_error_handling(self) -> None:
        """Test uninstall error handling."""
        status = Mock()
        status.base_path = Mock()
        status.base_path.exists.return_value = True

        self.mock_console.input.return_value = "yes"

        with patch("shutil.rmtree", side_effect=OSError("Permission denied")):
            with pytest.raises(InstallationError, match="Base uninstall failed"):
                self.installer._uninstall_base(status)
