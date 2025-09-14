"""Tests for AgentOS configuration management."""

import json
import sys
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

import pytest
import yaml

from agent_os_cli.core.config import ConfigManager
from agent_os_cli.types import AgentType, ConfigurationError


class TestConfigManager:
    """Test ConfigManager functionality."""

    def setup_method(self) -> None:
        """Set up test environment."""
        self.config_manager = ConfigManager()

    def test_init(self) -> None:
        """Test ConfigManager initialization."""
        assert self.config_manager._base_config_cache is None
        assert self.config_manager._status_cache is None

    def test_get_base_config_success(self) -> None:
        """Test successful base configuration loading."""
        # Create a valid config
        config_data = {
            "agent_os_version": "1.4.2",
            "agents": {
                "claude_code": {"enabled": True},
                "cursor": {"enabled": False},
            },
            "project_types": {
                "default": {
                    "instructions": "Default instructions",
                    "standards": "Default standards",
                }
            },
            "default_project_type": "default",
        }

        with tempfile.TemporaryDirectory() as temp_dir:
            # Create .agent-os directory
            agent_os_dir = Path(temp_dir) / ".agent-os"
            agent_os_dir.mkdir(parents=True)

            config_path = agent_os_dir / "config.yml"
            with config_path.open("w", encoding="utf-8") as f:
                yaml.dump(config_data, f)

            with patch("pathlib.Path.home") as mock_home:
                mock_home.return_value = Path(temp_dir)
                config = self.config_manager.get_base_config()

                assert config.agent_os_version == "1.4.2"
                assert AgentType.CLAUDE_CODE in config.agents
                assert config.agents[AgentType.CLAUDE_CODE].enabled is True
                assert "default" in config.project_types

    def test_get_base_config_not_found(self) -> None:
        """Test base config when file doesn't exist."""
        with tempfile.TemporaryDirectory() as temp_dir:
            with patch("pathlib.Path.home") as mock_home:
                mock_home.return_value = Path(temp_dir)

                with pytest.raises(ConfigurationError, match="Base AgentOS configuration not found"):
                    self.config_manager.get_base_config()

    def test_get_base_config_invalid_yaml(self) -> None:
        """Test base config with invalid YAML."""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir) / ".agent-os" / "config.yml"
            config_path.parent.mkdir(parents=True)

            # Write invalid YAML
            with config_path.open("w", encoding="utf-8") as f:
                f.write("invalid: yaml: content: [")

            with patch("pathlib.Path.home") as mock_home:
                mock_home.return_value = Path(temp_dir)

                with pytest.raises(ConfigurationError, match="Invalid YAML"):
                    self.config_manager.get_base_config()

    def test_get_base_config_validation_error(self) -> None:
        """Test base config with validation errors."""
        # Create invalid config (missing required fields)
        config_data = {"invalid": "config"}

        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir) / ".agent-os" / "config.yml"
            config_path.parent.mkdir(parents=True)

            with config_path.open("w", encoding="utf-8") as f:
                yaml.dump(config_data, f)

            with patch("pathlib.Path.home") as mock_home:
                mock_home.return_value = Path(temp_dir)

                with pytest.raises(ConfigurationError, match="Configuration validation failed"):
                    self.config_manager.get_base_config()

    def test_get_base_config_caching(self) -> None:
        """Test that base config is cached properly."""
        config_data = {
            "agent_os_version": "1.4.2",
            "agents": {},
            "project_types": {"default": {"instructions": "test", "standards": "test"}},
        }

        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir) / ".agent-os" / "config.yml"
            config_path.parent.mkdir(parents=True)

            with config_path.open("w", encoding="utf-8") as f:
                yaml.dump(config_data, f)

            with patch("pathlib.Path.home") as mock_home:
                mock_home.return_value = Path(temp_dir)

                # First call should load from file
                config1 = self.config_manager.get_base_config()
                assert self.config_manager._base_config_cache is not None

                # Second call should use cache
                config2 = self.config_manager.get_base_config()
                assert config1 is config2  # Same object instance

    def test_get_install_status_no_installations(self) -> None:
        """Test install status with no installations."""
        with tempfile.TemporaryDirectory() as temp_dir:
            with patch("pathlib.Path.home") as mock_home, patch("pathlib.Path.cwd") as mock_cwd:
                mock_home.return_value = Path(temp_dir)
                mock_cwd.return_value = Path(temp_dir)

                status = self.config_manager.get_install_status()

                assert status.base_installed is False
                assert status.base_path is None
                assert status.base_version is None
                assert status.project_installed is False
                assert status.project_path is None
                assert status.project_agents == []
                assert status.project_type is None

    def test_get_install_status_base_only(self) -> None:
        """Test install status with base installation only."""
        config_data = {
            "agent_os_version": "1.4.2",
            "agents": {},
            "project_types": {"default": {"instructions": "test", "standards": "test"}},
        }

        with tempfile.TemporaryDirectory() as temp_dir:
            # Create base installation
            base_path = Path(temp_dir) / ".agent-os"
            base_path.mkdir(parents=True)

            config_path = base_path / "config.yml"
            with config_path.open("w", encoding="utf-8") as f:
                yaml.dump(config_data, f)

            with patch("pathlib.Path.home") as mock_home, patch("pathlib.Path.cwd") as mock_cwd:
                mock_home.return_value = Path(temp_dir)
                mock_cwd.return_value = Path(temp_dir) / "project"

                status = self.config_manager.get_install_status()

                assert status.base_installed is True
                assert status.base_version == "1.4.2"
                assert status.project_installed is False

    def test_get_install_status_project_with_agents(self) -> None:
        """Test install status with project installation and agents."""
        with tempfile.TemporaryDirectory() as temp_dir:
            project_dir = Path(temp_dir) / "project"
            project_dir.mkdir(parents=True)

            # Create project installation with agent files
            agent_os_dir = project_dir / ".agent-os"
            agent_os_dir.mkdir(parents=True)

            # Claude Code integration
            (agent_os_dir / "CLAUDE.md").write_text("Claude instructions")

            # Cursor integration
            (agent_os_dir / ".cursorrules").write_text("Cursor rules")

            # Create project files for type detection
            (project_dir / "pyproject.toml").write_text("[project]")

            with patch("pathlib.Path.home") as mock_home, patch("pathlib.Path.cwd") as mock_cwd:
                mock_home.return_value = Path(temp_dir) / "home"
                mock_cwd.return_value = project_dir

                status = self.config_manager.get_install_status()

                assert status.base_installed is False
                assert status.project_installed is True
                assert AgentType.CLAUDE_CODE in status.project_agents
                assert AgentType.CURSOR in status.project_agents
                assert status.project_type == "python-modern"

    def test_detect_project_type_python_variants(self) -> None:
        """Test project type detection for Python variants."""
        test_cases = [
            (["pyproject.toml"], "python-modern"),
            (["poetry.lock"], "python-poetry"),
            (["uv.lock"], "python-uv"),
            (["setup.py"], "python"),
            (["requirements.txt"], "python"),
        ]

        for files, expected_type in test_cases:
            with tempfile.TemporaryDirectory() as temp_dir:
                project_root = Path(temp_dir)

                for file_name in files:
                    (project_root / file_name).write_text("test content")

                result = self.config_manager._detect_project_type(project_root)
                assert result == expected_type

    def test_detect_project_type_javascript_variants(self) -> None:
        """Test project type detection for JavaScript variants."""
        # Test Next.js detection
        with tempfile.TemporaryDirectory() as temp_dir:
            project_root = Path(temp_dir)

            package_json_content = {"dependencies": {"next": "^13.0.0", "react": "^18.0.0"}}

            with (project_root / "package.json").open("w") as f:
                json.dump(package_json_content, f)

            result = self.config_manager._detect_project_type(project_root)
            assert result == "javascript-nextjs"

        # Test React detection
        with tempfile.TemporaryDirectory() as temp_dir:
            project_root = Path(temp_dir)

            package_json_content = {"dependencies": {"react": "^18.0.0"}}

            with (project_root / "package.json").open("w") as f:
                json.dump(package_json_content, f)

            result = self.config_manager._detect_project_type(project_root)
            assert result == "javascript-react"

    def test_detect_project_type_other_languages(self) -> None:
        """Test project type detection for other languages."""
        test_cases = [
            (["Cargo.toml"], "rust"),
            (["go.mod"], "go"),
            (["pom.xml"], "java-maven"),
            (["build.gradle"], "java-gradle"),
            (["CMakeLists.txt"], "cpp"),
            (["index.html"], "web"),
        ]

        for files, expected_type in test_cases:
            with tempfile.TemporaryDirectory() as temp_dir:
                project_root = Path(temp_dir)

                for file_name in files:
                    (project_root / file_name).write_text("test content")

                result = self.config_manager._detect_project_type(project_root)
                assert result == expected_type

    def test_detect_project_type_default_fallback(self) -> None:
        """Test project type detection fallback to default."""
        with tempfile.TemporaryDirectory() as temp_dir:
            project_root = Path(temp_dir)
            # No recognizable project files

            result = self.config_manager._detect_project_type(project_root)
            assert result == "default"

    def test_detect_project_agents_none(self) -> None:
        """Test agent detection with no agents configured."""
        with tempfile.TemporaryDirectory() as temp_dir:
            project_path = Path(temp_dir)

            agents = self.config_manager._detect_project_agents(project_path)
            assert agents == []

    def test_detect_project_agents_claude_code(self) -> None:
        """Test Claude Code agent detection."""
        with tempfile.TemporaryDirectory() as temp_dir:
            project_path = Path(temp_dir)
            (project_path / "CLAUDE.md").write_text("Claude instructions")

            agents = self.config_manager._detect_project_agents(project_path)
            assert agents == [AgentType.CLAUDE_CODE]

    def test_detect_project_agents_cursor(self) -> None:
        """Test Cursor agent detection."""
        with tempfile.TemporaryDirectory() as temp_dir:
            project_path = Path(temp_dir)
            (project_path / ".cursorrules").write_text("Cursor rules")

            agents = self.config_manager._detect_project_agents(project_path)
            assert agents == [AgentType.CURSOR]

    def test_detect_project_agents_both(self) -> None:
        """Test detection of multiple agents."""
        with tempfile.TemporaryDirectory() as temp_dir:
            project_path = Path(temp_dir)
            (project_path / "CLAUDE.md").write_text("Claude instructions")
            (project_path / ".cursorrules").write_text("Cursor rules")

            agents = self.config_manager._detect_project_agents(project_path)
            assert set(agents) == {AgentType.CLAUDE_CODE, AgentType.CURSOR}

    def test_install_status_caching(self) -> None:
        """Test that install status is cached properly."""
        with tempfile.TemporaryDirectory() as temp_dir:
            with patch("pathlib.Path.home") as mock_home, patch("pathlib.Path.cwd") as mock_cwd:
                mock_home.return_value = Path(temp_dir)
                mock_cwd.return_value = Path(temp_dir)

                # First call should scan filesystem
                status1 = self.config_manager.get_install_status()
                assert self.config_manager._status_cache is not None

                # Second call should use cache
                status2 = self.config_manager.get_install_status()
                assert status1 is status2  # Same object instance

    def test_clear_cache(self) -> None:
        """Test cache clearing functionality."""
        # Set some cached values
        self.config_manager._base_config_cache = Mock()
        self.config_manager._status_cache = Mock()

        # Clear cache
        self.config_manager.clear_cache()

        # Verify cache is cleared
        assert self.config_manager._base_config_cache is None
        assert self.config_manager._status_cache is None

    def test_get_base_config_invalid_format(self) -> None:
        """Test base config with invalid format (not dict)."""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir) / ".agent-os" / "config.yml"
            config_path.parent.mkdir(parents=True)

            # Write YAML that parses to a string, not dict
            with config_path.open("w", encoding="utf-8") as f:
                f.write("just a string")

            with patch("pathlib.Path.home") as mock_home:
                mock_home.return_value = Path(temp_dir)

                with pytest.raises(ConfigurationError, match="Invalid configuration format"):
                    self.config_manager.get_base_config()

    def test_get_base_config_io_error(self) -> None:
        """Test base config with I/O error."""
        if sys.platform == "win32":
            # On Windows, simulate I/O error by mocking Path.open directly
            with tempfile.TemporaryDirectory() as temp_dir:
                config_path = Path(temp_dir) / ".agent-os" / "config.yml"
                config_path.parent.mkdir(parents=True)
                config_path.write_text("test: content")

                with patch("pathlib.Path.home") as mock_home:
                    mock_home.return_value = Path(temp_dir)

                    # Mock Path.open to raise PermissionError
                    with patch.object(Path, "open", side_effect=PermissionError("Simulated I/O error")):
                        with pytest.raises(ConfigurationError, match="Failed to read configuration file"):
                            self.config_manager.get_base_config()
        else:
            # On Unix systems, use chmod to make file unreadable
            with tempfile.TemporaryDirectory() as temp_dir:
                config_path = Path(temp_dir) / ".agent-os" / "config.yml"
                config_path.parent.mkdir(parents=True)
                config_path.write_text("test: content")

                # Make file unreadable
                config_path.chmod(0o000)

                with patch("pathlib.Path.home") as mock_home:
                    mock_home.return_value = Path(temp_dir)

                    try:
                        with pytest.raises(ConfigurationError, match="Failed to read configuration file"):
                            self.config_manager.get_base_config()
                    finally:
                        # Restore permissions for cleanup
                        config_path.chmod(0o644)
