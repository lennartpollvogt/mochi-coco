"""Version utilities for Mochi-Coco."""

import importlib.metadata
import re
from pathlib import Path


def get_version() -> str:
    """Get the current version of mochi-coco."""
    try:
        return importlib.metadata.version("mochi-coco")
    except importlib.metadata.PackageNotFoundError:
        return _get_version_from_pyproject()


def _get_version_from_pyproject() -> str:
    """Get version by parsing pyproject.toml with regex."""
    try:
        current_dir = Path(__file__).parent
        for parent in [current_dir] + list(current_dir.parents):
            pyproject_path = parent / "pyproject.toml"
            if pyproject_path.exists():
                content = pyproject_path.read_text(encoding="utf-8")
                match = re.search(r'version\s*=\s*["\']([^"\']+)["\']', content)
                if match:
                    return match.group(1)
        return "unknown"
    except Exception:
        return "unknown"
