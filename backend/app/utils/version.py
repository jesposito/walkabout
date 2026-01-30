"""Version utilities for Walkabout."""

from pathlib import Path
from functools import lru_cache


@lru_cache(maxsize=1)
def get_version() -> str:
    """Read the current version from LATEST_VERSION file.

    Cached to avoid repeated file reads.
    """
    possible_paths = [
        Path(__file__).parent.parent.parent.parent / "LATEST_VERSION",  # repo root
        Path("/app/LATEST_VERSION"),  # Docker container path
        Path.cwd() / "LATEST_VERSION",  # Current working directory
    ]

    for path in possible_paths:
        if path.exists():
            return path.read_text().strip()

    return "v0.0.0-dev"


@lru_cache(maxsize=1)
def get_changelog() -> str:
    """Read the changelog content.

    Cached to avoid repeated file reads.
    """
    possible_paths = [
        Path(__file__).parent.parent.parent.parent / "CHANGELOG.md",
        Path("/app/CHANGELOG.md"),
        Path.cwd() / "CHANGELOG.md",
    ]

    for path in possible_paths:
        if path.exists():
            return path.read_text()

    return "# Changelog\n\nNo changelog available."
