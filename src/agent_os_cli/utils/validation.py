"""Validation utilities for AgentOS."""

import re
from typing import Optional


def validate_project_type(project_type: Optional[str]) -> None:
    """Validate project type string for security and format.

    Args:
        project_type: The project type string to validate

    Raises:
        ValueError: If the project type is invalid
    """
    if not project_type:
        raise ValueError("Project type cannot be empty")

    # Security: Prevent directory traversal
    if ".." in project_type or "/" in project_type or "\\" in project_type:
        raise ValueError(f"Invalid project type: {project_type}")

    # Only allow alphanumeric, dash, and underscore
    if not re.match(r"^[a-zA-Z0-9_-]+$", project_type):
        raise ValueError(
            f"Project type must contain only alphanumeric characters, dashes, and underscores: {project_type}"
        )

    # Prevent special names that could be problematic
    if project_type.startswith(("-", "_")) or project_type.endswith(("-", "_")):
        raise ValueError(f"Project type cannot start or end with dash or underscore: {project_type}")

    # Additional security checks
    dangerous_patterns = ["$", "|", ";", "&", "`", "(", ")", "{", "}", "[", "]", "<", ">", "!", "\\n", "\\t"]
    for pattern in dangerous_patterns:
        if pattern in project_type:
            raise ValueError(f"Invalid character in project type: {project_type}")
