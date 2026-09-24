from __future__ import annotations
from pathlib import Path
import subprocess

# Optional: expliziter Git-Bash-Pfad (Windows)
GIT_BASH = Path(r"C:\Program Files\Git\bin\bash.exe")


def _find_project_root(start: Path | str) -> Path:
    """Find the repository root containing the flat scripts and firmware."""
    p = Path(start).resolve()
    if p.is_file():
        p = p.parent
    for parent in [p] + list(p.parents):
        if (parent / "analysis" / "python_ui" / "app.py").is_file() and \
                (parent / "firmware").is_dir():
            return parent
    return Path(__file__).resolve().parents[2]


def run_bash(script_path: Path, args: list[str]) -> str:
    """
    Führt ein Bash-Skript relativ zum Projekt-Root aus.
    """
    script_path = Path(script_path).resolve()

    if not script_path.exists():
        return f"[ERROR] Script nicht gefunden: {script_path}"

    project_root = _find_project_root(script_path)

    # Skript relativ zum Projekt-Root
    rel_script = script_path.relative_to(project_root).as_posix()

    bash_exe = str(GIT_BASH) if GIT_BASH.exists() else "bash"

    cmd = [bash_exe, rel_script, *args]

    p = subprocess.run(
        cmd,
        cwd=str(project_root),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )

    return ((p.stdout or "") + (p.stderr or "")).strip()
