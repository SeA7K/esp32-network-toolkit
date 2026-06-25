from pathlib import Path

# Datei liegt in: ESP32_terminal/analysis/python_ui/config.py
# parents[0] = python_ui
# parents[1] = analysis
# parents[2] = ESP32_terminal   ✅
BASE_DIR = Path(__file__).resolve().parents[2]

LOG_DIR = BASE_DIR / "logs"
LOGS_NORMALIZED_DIR = BASE_DIR / "logs_normalized"
REPORT_DIR = BASE_DIR / "reports"
HOST_BASH_DIR = BASE_DIR / "host" / "bash"

COLORS = {
    "title": "bold cyan",
    "ok": "green",
    "warn": "yellow",
    "error": "red",
    "info": "bright_blue",
}
