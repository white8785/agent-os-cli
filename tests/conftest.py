"""Shared pytest fixtures and configuration for AgentOS tests."""

import tempfile
from collections.abc import Generator
from pathlib import Path

import pytest


@pytest.fixture
def temp_dir() -> Generator[Path, None, None]:
    """Provide a temporary directory for testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def mock_home_dir(temp_dir: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Mock the home directory for testing."""
    home_dir = temp_dir / "home"
    home_dir.mkdir(exist_ok=True)
    monkeypatch.setattr(Path, "home", lambda: home_dir)
    return home_dir


@pytest.fixture
def mock_project_dir(temp_dir: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Mock a project directory for testing."""
    project_dir = temp_dir / "project"
    project_dir.mkdir(exist_ok=True)
    monkeypatch.chdir(project_dir)
    return project_dir
