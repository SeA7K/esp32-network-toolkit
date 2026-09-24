from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path


def _bash_path_to_windows(path_str: str) -> str:
    """
    Konvertiert Git-Bash Pfade wie /c/Users/... nach C:\\Users\\...
    Lässt Windows-Pfade unverändert.
    """
    s = path_str.strip()

    # Git-Bash: /c/Users/...  ->  C:\Users\...
    if s.startswith("/c/"):
        return "C:\\" + s[3:].replace("/", "\\")

    # Git-Bash: /d/... -> D:\...
    if len(s) >= 3 and s[0] == "/" and s[2] == "/":
        drive = s[1].upper()
        return drive + ":\\" + s[3:].replace("/", "\\")

    # Bereits Windows-Pfad
    return s


def extract_logfile_from_output(output: str) -> Path | None:
    """
    Sucht in der Ausgabe nach: 'Logfile: <pfad>'
    Gibt den Pfad als Path zurück oder None.
    """
    m = re.search(r"Logfile:\s*(.+)", output)
    if not m:
        return None

    raw_path = m.group(1).strip()
    win_path = _bash_path_to_windows(raw_path)

    return Path(win_path).expanduser()


def generate_report_for_log(log_path: Path) -> tuple[bool, str]:
    """
    Ruft report_gen.py mit dem gegebenen Logfile auf.
    Returns: (ok, message)
    """
    if not str(log_path).strip():
        return False, "[AUTO-REPORT] Fehler: Log-Pfad ist leer."

    if not log_path.exists():
        return False, f"[AUTO-REPORT] Fehler: Log existiert nicht: {log_path}"

    if log_path.is_dir():
        return False, f"[AUTO-REPORT] Fehler: Log-Pfad ist ein Ordner: {log_path}"

    report_script = Path(__file__).resolve().parent / "report_gen.py"
    if not report_script.exists():
        return False, f"[AUTO-REPORT] Fehler: report_gen.py nicht gefunden: {report_script}"

    p = subprocess.run(
        [sys.executable, str(report_script), str(log_path)],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )

    out = ((p.stdout or "") + (p.stderr or "")).strip()
    if p.returncode == 0:
        return True, "[AUTO-REPORT] OK\n" + out

    return False, "[AUTO-REPORT] FEHLER\n" + out


def auto_report_from_output(output: str) -> str:
    """
    Alles in einem:
    - Logfile aus Output ziehen
    - Report generieren
    - Status-Text zurückgeben
    """
    log_path = extract_logfile_from_output(output)
    if log_path is None:
        return "[AUTO-REPORT] Kein 'Logfile:' in der Ausgabe gefunden."

    ok, msg = generate_report_for_log(log_path)
    return msg
