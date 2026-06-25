from __future__ import annotations
from pathlib import Path

def project_root(start: Path | None = None) -> Path:
    """
    Läuft nach oben und sucht den Projekt-Root, der diese Ordner enthält:
    host/  logs/  data/  (mindestens 2 davon reichen)
    """
    cur = (start or Path(__file__)).resolve()
    for _ in range(25):
        has_host = (cur / "host").exists()
        has_logs = (cur / "logs").exists()
        has_data = (cur / "data").exists()
        if sum([has_host, has_logs, has_data]) >= 2:
            return cur
        cur = cur.parent
    # Fallback: 3 Ebenen hoch (analysis/python_ui -> analysis -> ESP32_Terminal)
    return Path(__file__).resolve().parents[2]
