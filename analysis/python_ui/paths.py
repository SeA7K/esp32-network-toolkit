from __future__ import annotations
from pathlib import Path

def project_root(start: Path | None = None) -> Path:
    """Find the flat repository root, even when called with a child path."""
    current = (start or Path(__file__)).resolve()
    if current.is_file():
        current = current.parent

    for parent in (current, *current.parents):
        if (parent / "analysis" / "python_ui" / "app.py").is_file() and \
                (parent / "host" / "bash").is_dir() and (parent / "firmware").is_dir():
            return parent

    return Path(__file__).resolve().parents[2]
