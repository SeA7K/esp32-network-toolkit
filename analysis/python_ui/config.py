from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[2]

LOG_DIR = BASE_DIR / "logs"
LOGS_NORMALIZED_DIR = BASE_DIR / "logs_normalized"
REPORT_DIR = BASE_DIR / "analysis" / "reports"
HOST_BASH_DIR = BASE_DIR / "host" / "bash"

COLORS = {
    "title": "bold cyan",
    "ok": "green",
    "warn": "yellow",
    "error": "red",
    "info": "bright_blue",
}
