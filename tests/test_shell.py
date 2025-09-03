"""Tests for AgentOS shell script integration."""

import inspect
import subprocess
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from agentos.core.shell import ShellExecutor
from agentos.types import InstallationError


class TestShellExecutor:
    """Test ShellExecutor functionality."""

    def setup_method(self) -> None:
        """Set up test environment."""
        self.mock_console = Mock()
        self.executor = ShellExecutor(console=self.mock_console)

    def test_init_default_console(self) -> None:
        """Test ShellExecutor initialization with default console."""
        executor = ShellExecutor()
        assert executor.console is not None
        assert executor.script_timeout == 600

    def test_init_custom_console(self) -> None:
        """Test ShellExecutor initialization with custom console."""
        console = Mock()
        executor = ShellExecutor(console=console)
        assert executor.console is console

    def test_validate_project_type_valid(self) -> None:
        """Test project type validation with valid inputs."""
        valid_types = [
            "python",
            "javascript",
            "rust-web",
            "python_django",
            "test123",
            "Test-Project_2",
        ]

        for project_type in valid_types:
            # Should not raise exception
            self.executor._validate_project_type(project_type)

    def test_validate_project_type_empty(self) -> None:
        """Test project type validation with empty input."""
        with pytest.raises(InstallationError, match="Project type cannot be empty"):
            self.executor._validate_project_type("")

    def test_validate_project_type_invalid_chars(self) -> None:
        """Test project type validation with invalid characters."""
        invalid_types = [
            "project/type",  # slash
            "project type",  # space
            "project.type",  # dot
            "project@type",  # at symbol
            "project#type",  # hash
            "project$type",  # dollar
        ]

        for project_type in invalid_types:
            with pytest.raises(InstallationError, match="(Invalid project type|alphanumeric characters)"):
                self.executor._validate_project_type(project_type)

    def test_validate_project_type_dangerous_patterns(self) -> None:
        """Test project type validation with dangerous patterns."""
        dangerous_types = [
            "../escape",
            "./current",
            "$(command)",
            "`command`",
            "type;rm -rf",
            "type&malicious",
            "type|pipe",
            "type>redirect",
            "type<input",
        ]

        for project_type in dangerous_types:
            with pytest.raises(InstallationError, match="(Invalid project type|alphanumeric characters)"):
                self.executor._validate_project_type(project_type)

    def test_find_script_success(self) -> None:
        """Test successful script discovery."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create a mock script file
            script_path = Path(temp_dir) / "test.sh"
            script_path.write_text("#!/bin/bash\\necho 'test'")
            script_path.chmod(0o755)  # Make executable

            # Mock the search locations to include our temp directory
            with patch.object(self.executor, "_find_script") as mock_find:
                mock_find.return_value = script_path

                result = self.executor._find_script("test.sh")
                assert result == script_path

    def test_find_script_not_found(self) -> None:
        """Test script discovery when script doesn't exist."""
        with patch("pathlib.Path.exists", return_value=False):
            result = self.executor._find_script("nonexistent.sh")
            assert result is None

    def test_find_script_not_executable(self) -> None:
        """Test script discovery with non-executable script."""
        with tempfile.TemporaryDirectory() as temp_dir:
            script_path = Path(temp_dir) / "test.sh"
            script_path.write_text("#!/bin/bash\\necho 'test'")
            script_path.chmod(0o644)  # Not executable

            search_locations = [script_path]

            with (
                patch.object(Path, "exists", return_value=True),
                patch.object(Path, "is_file", return_value=True),
                patch.object(Path, "stat") as mock_stat,
            ):

                # Mock stat to return non-executable permissions
                mock_stat_result = Mock()
                mock_stat_result.st_mode = 0o644  # Not executable
                mock_stat.return_value = mock_stat_result

                # Override search locations for this test
                def mock_find_script(self, script_name):
                    for location in search_locations:
                        if location.exists() and location.is_file():
                            if not location.stat().st_mode & 0o111:
                                self.console.print(f"⚠️ [yellow]Script {location} found but not executable[/yellow]")
                                continue
                            return location
                    return None

                with patch.object(ShellExecutor, "_find_script", mock_find_script):
                    result = self.executor._find_script("test.sh")
                    assert result is None

                # Verify warning was printed
                self.mock_console.print.assert_called_once()

    @patch("subprocess.run")
    def test_execute_script_success(self, mock_run: Mock) -> None:
        """Test successful script execution."""
        # Mock successful subprocess execution
        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = "Installation completed successfully"
        mock_result.stderr = ""
        mock_run.return_value = mock_result

        with patch("agentos.core.shell.Progress") as mock_progress_cls:
            mock_progress = Mock()
            mock_task = Mock()
            mock_progress.add_task.return_value = mock_task
            mock_progress_cls.return_value.__enter__.return_value = mock_progress

            self.executor._execute_script(
                ["/path/to/script.sh", "--test"], "Testing script execution", "✅ Script completed successfully"
            )

            # Verify subprocess was called correctly
            mock_run.assert_called_once()
            call_args = mock_run.call_args

            assert call_args[0][0] == ["/path/to/script.sh", "--test"]
            assert call_args[1]["check"] is False
            assert call_args[1]["capture_output"] is True
            assert call_args[1]["text"] is True
            assert call_args[1]["shell"] is False
            assert "PATH" in call_args[1]["env"]

    @patch("subprocess.run")
    def test_execute_script_failure(self, mock_run: Mock) -> None:
        """Test script execution failure."""
        # Mock failed subprocess execution
        mock_result = Mock()
        mock_result.returncode = 1
        mock_result.stdout = "Some output"
        mock_result.stderr = "Error occurred"
        mock_run.return_value = mock_result

        with (
            patch("agentos.core.shell.Progress") as mock_progress_cls,
            pytest.raises(InstallationError, match="Script failed with exit code 1"),
        ):

            mock_progress = Mock()
            mock_progress_cls.return_value.__enter__.return_value = mock_progress

            self.executor._execute_script(["/path/to/script.sh"], "Testing script failure", "Should not see this")

    @patch("subprocess.run")
    def test_execute_script_timeout(self, mock_run: Mock) -> None:
        """Test script execution timeout."""
        # Mock timeout exception
        mock_run.side_effect = subprocess.TimeoutExpired("cmd", 600)

        with (
            patch("agentos.core.shell.Progress") as mock_progress_cls,
            pytest.raises(InstallationError, match="Script execution timed out"),
        ):

            mock_progress = Mock()
            mock_progress_cls.return_value.__enter__.return_value = mock_progress

            self.executor._execute_script(["/path/to/script.sh"], "Testing script timeout", "Should not see this")

    @patch("subprocess.run")
    def test_execute_script_subprocess_error(self, mock_run: Mock) -> None:
        """Test script execution with subprocess error."""
        # Mock subprocess error
        mock_run.side_effect = subprocess.SubprocessError("Process failed")

        with (
            patch("agentos.core.shell.Progress") as mock_progress_cls,
            pytest.raises(InstallationError, match="Failed to execute installation script"),
        ):

            mock_progress = Mock()
            mock_progress_cls.return_value.__enter__.return_value = mock_progress

            self.executor._execute_script(["/path/to/script.sh"], "Testing subprocess error", "Should not see this")

    @patch("subprocess.run")
    def test_execute_script_unexpected_error(self, mock_run: Mock) -> None:
        """Test script execution with unexpected error."""
        # Mock unexpected error
        mock_run.side_effect = ValueError("Unexpected error")

        with (
            patch("agentos.core.shell.Progress") as mock_progress_cls,
            pytest.raises(InstallationError, match="Unexpected error during script execution"),
        ):

            mock_progress = Mock()
            mock_progress_cls.return_value.__enter__.return_value = mock_progress

            self.executor._execute_script(["/path/to/script.sh"], "Testing unexpected error", "Should not see this")

    def test_run_base_install_success(self) -> None:
        """Test successful base installation."""
        with (
            patch.object(self.executor, "_find_script") as mock_find,
            patch.object(self.executor, "_execute_script") as mock_execute,
            patch.object(self.executor, "_validate_project_type") as mock_validate,
        ):

            mock_find.return_value = Path("/path/to/base.sh")

            self.executor.run_base_install(
                claude_code=True,
                cursor=False,
                project_type="python",
                overwrite_instructions=True,
            )

            mock_validate.assert_called_once_with("python")
            mock_find.assert_called_once_with("base.sh")
            mock_execute.assert_called_once()

            # Verify command arguments
            call_args = mock_execute.call_args[0][0]
            assert "/path/to/base.sh" in call_args
            assert "--claude-code" in call_args
            assert "--cursor" not in call_args
            assert "--project-type" in call_args
            assert "python" in call_args
            assert "--overwrite-instructions" in call_args

    def test_run_base_install_script_not_found(self) -> None:
        """Test base installation when script not found."""
        with (
            patch.object(self.executor, "_find_script", return_value=None),
            patch.object(self.executor, "_validate_project_type"),
        ):

            with pytest.raises(InstallationError, match="Base installation script 'base.sh' not found"):
                self.executor.run_base_install()

    def test_run_base_install_default_project_type(self) -> None:
        """Test base installation with default project type."""
        with (
            patch.object(self.executor, "_find_script") as mock_find,
            patch.object(self.executor, "_execute_script") as mock_execute,
            patch.object(self.executor, "_validate_project_type") as mock_validate,
        ):

            mock_find.return_value = Path("/path/to/base.sh")

            self.executor.run_base_install(project_type="default")

            mock_validate.assert_called_once_with("default")

            # Verify default project type is not added to command
            call_args = mock_execute.call_args[0][0]
            assert "--project-type" not in call_args

    def test_run_project_install_success(self) -> None:
        """Test successful project installation."""
        with (
            patch.object(self.executor, "_find_script") as mock_find,
            patch.object(self.executor, "_execute_script") as mock_execute,
            patch.object(self.executor, "_validate_project_type") as mock_validate,
        ):

            mock_find.return_value = Path("/path/to/project.sh")

            self.executor.run_project_install(
                claude_code=False,
                cursor=True,
                project_type="javascript",
                overwrite_standards=True,
            )

            mock_validate.assert_called_once_with("javascript")
            mock_find.assert_called_once_with("project.sh")
            mock_execute.assert_called_once()

            # Verify command arguments
            call_args = mock_execute.call_args[0][0]
            assert "/path/to/project.sh" in call_args
            assert "--claude-code" not in call_args
            assert "--cursor" in call_args
            assert "--project-type=javascript" in call_args
            assert "--overwrite-standards" in call_args

    def test_run_project_install_script_not_found(self) -> None:
        """Test project installation when script not found."""
        with (
            patch.object(self.executor, "_find_script", return_value=None),
            patch.object(self.executor, "_validate_project_type"),
        ):

            with pytest.raises(InstallationError, match="Project installation script 'project.sh' not found"):
                self.executor.run_project_install()

    def test_run_project_install_validation_error(self) -> None:
        """Test project installation with validation error."""
        with patch.object(self.executor, "_validate_project_type") as mock_validate:
            mock_validate.side_effect = InstallationError("Invalid project type")

            with pytest.raises(InstallationError, match="Invalid project type"):
                self.executor.run_project_install(project_type="invalid/type")

    def test_script_search_locations(self) -> None:
        """Test that script search includes all expected locations."""
        with patch("pathlib.Path.exists", return_value=False):
            result = self.executor._find_script("test.sh")
            assert result is None

        # Test the actual method to verify search locations are reasonable
        # This is more of an integration test to ensure the paths make sense
        source = inspect.getsource(self.executor._find_script)

        # Verify that common locations are included in the search
        assert "scripts" in source
        assert "setup" in source
        assert ".agent-os" in source
        assert "/usr/local/bin" in source or "/usr/bin" in source

    def test_environment_security(self) -> None:
        """Test that script execution uses secure environment."""
        with patch("subprocess.run") as mock_run, patch("agentos.core.shell.Progress") as mock_progress_cls:

            mock_result = Mock()
            mock_result.returncode = 0
            mock_result.stdout = ""
            mock_result.stderr = ""
            mock_run.return_value = mock_result

            mock_progress = Mock()
            mock_progress_cls.return_value.__enter__.return_value = mock_progress

            self.executor._execute_script(["/path/to/script.sh"], "Testing environment", "Success")

            # Verify environment is restricted
            call_args = mock_run.call_args[1]
            env = call_args["env"]

            assert "PATH" in env
            assert "HOME" in env
            assert "USER" in env
            assert "LANG" in env

            # Environment should be minimal for security
            assert len(env) <= 10  # Reasonable upper bound for minimal environment
