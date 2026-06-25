from __future__ import annotations

import re
import subprocess
from pathlib import Path

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from runner import run_bash
from db import last_scans
from import_log_to_db import import_log_to_db
from log_normalizer import write_normalized
from auto_report import auto_report_from_output

console = Console()


def get_project_root() -> Path:
    """
    Sucht Projekt-Root, indem es nach oben läuft und 'host' + 'logs' findet.
    Funktioniert egal ob:
    - .../ESP32_Terminal/analysis/python_ui/app.py
    - .../ESP32_Terminal/python_ui/app.py
    """
    cur = Path(__file__).resolve()
    for _ in range(15):
        if (cur / "host").exists() and (cur / "logs").exists():
            return cur
        cur = cur.parent
    return Path(__file__).resolve().parents[2]


BASE_DIR = get_project_root()

LOG_DIR = BASE_DIR / "logs"
NORM_LOG_DIR = BASE_DIR / "logs_normalized"
REPORT_DIR = BASE_DIR / "analysis" / "reports"

HOST_DIR = BASE_DIR / "host"
BASH_DIR = HOST_DIR / "bash"

SCRIPTS = {
    "bridge": BASH_DIR / "esp32_bridge.sh",
    "target": BASH_DIR / "esp32_target.sh",
    "summary": BASH_DIR / "esp32_summary.sh",
    "profile_filter": BASH_DIR / "esp32_profile_filter.sh",
    "detect_profile": BASH_DIR / "esp32_detect_profile.sh",
    "report_gen": Path(__file__).resolve().parent / "report_gen.py",
}


def ensure_dirs():
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    NORM_LOG_DIR.mkdir(parents=True, exist_ok=True)
    REPORT_DIR.mkdir(parents=True, exist_ok=True)


def header():
    console.print(Panel("ESP32 Network Toolkit – Python UI", style="bold cyan"))


def menu():
    console.print("[bold]1)[/] WLAN Scan (ESP32)")
    console.print("[bold]2)[/] LAN Discovery (ESP32)")
    console.print("[bold]3)[/] Combo Scan (ESP32)")
    console.print("[bold]4)[/] Router/Gateway Scan (ESP32)")
    console.print("[bold]5)[/] Target-IP Scan (ESP32)")
    console.print("[bold]6)[/] Summary aus Log")
    console.print("[bold]7)[/] Profile Filter (router/pc/server)")
    console.print("[bold]8)[/] Auto Profile (erkennen)")
    console.print("[bold]9)[/] Letzte Logs anzeigen")
    console.print("[bold]10)[/] Report (Markdown) erzeugen (manuell)")
    console.print("[bold]11)[/] Scan History (Datenbank)")
    console.print("[bold]0)[/] Beenden")


def list_latest_logs(n: int = 10) -> list[Path]:
    ensure_dirs()
    files = sorted(LOG_DIR.glob("*.txt"), key=lambda p: p.stat().st_mtime, reverse=True)
    return files[:n]


def show_logs_table(files: list[Path]):
    table = Table(title="Letzte Logs")
    table.add_column("#", style="bold cyan", width=3)
    table.add_column("Datei", style="white")
    for i, f in enumerate(files, start=1):
        table.add_row(str(i), f.name)
    console.print(table)


def pick_log() -> Path | None:
    files = list_latest_logs(10)
    if not files:
        console.print("[red]Keine Logs gefunden.[/red]")
        return None

    show_logs_table(files)
    choice = console.input("Log auswählen (Nummer) oder ENTER=neueste > ").strip()
    if choice == "":
        return files[0]

    if not choice.isdigit():
        console.print("[red]Ungültige Eingabe.[/red]")
        return None

    idx = int(choice) - 1
    if idx < 0 or idx >= len(files):
        console.print("[red]Nummer außerhalb Bereich.[/red]")
        return None

    return files[idx]


def ask_com_port(default: str = "COM3") -> str:
    com = console.input(f"COM Port (ENTER={default}) > ").strip()
    return com if com else default


def ask_seconds(default: str = "30") -> str:
    sec = console.input(f"Sekunden lesen (ENTER={default}) > ").strip()
    return sec if sec else default


def _check_scripts_exist() -> bool:
    ok = True
    for k, p in SCRIPTS.items():
        if k == "report_gen":
            continue
        if not Path(p).exists():
            console.print(f"[red]Script fehlt:[/red] {p}")
            ok = False
    return ok


def _bash_path_to_windows(s: str) -> str:
    """
    Konvertiert /c/Users/... nach C:\\Users\\...
    und /d/... nach D:\\...
    """
    s = s.strip()
    if s.startswith("/c/"):
        return "C:\\" + s[3:].replace("/", "\\")
    if len(s) >= 3 and s[0] == "/" and s[2] == "/":
        drive = s[1].upper()
        return drive + ":\\" + s[3:].replace("/", "\\")
    return s


def extract_logfile_path(output: str) -> Path | None:
    """
    Extrahiert den Logfile-Pfad direkt aus der Scan-Ausgabe:
    Zeile: 'Logfile: <pfad>'
    """
    m = re.search(r"Logfile:\s*(.+)", output)
    if not m:
        return None
    raw = m.group(1).strip()
    raw = _bash_path_to_windows(raw)
    return Path(raw).expanduser()


def _auto_report_from_logfile(log_path: Path):
    """
    auto_report_from_output() erwartet 'Logfile:' in einer Ausgabe.
    Wir geben ihm deshalb einen Fake-Output.
    """
    try:
        fake_out = f"Logfile: {log_path}"
        msg = auto_report_from_output(fake_out)
        console.print(msg)
    except Exception as e:
        console.print(f"[red]Auto-Report fehlgeschlagen:[/red] {e}")


def _post_process_log(original_log: Path, scan_type: str, com: str):
    """
    Original Log -> Normalized Log -> DB -> Auto Report
    """
    # Normalize
    norm_path = NORM_LOG_DIR / original_log.name.replace(".txt", "_normalized.txt")
    write_normalized(original_log, norm_path, scan_type=scan_type, com=com)
    console.print(f"[cyan]Normalized Log:[/cyan] {norm_path.name}")

    # DB Import
    try:
        scan_id = import_log_to_db(norm_path)
        console.print(f"[green]DB gespeichert[/green] ✅ ID={scan_id}")
    except Exception as e:
        console.print(f"[red]DB-Import fehlgeschlagen:[/red] {e}")

    # Auto Report
    console.print("[bold cyan]Auto-Report:[/bold cyan]")
    _auto_report_from_logfile(original_log)


# ---------------------------
# Scans
# ---------------------------
def run_bridge(cmd_num: str):
    if not _check_scripts_exist():
        console.input("\nENTER zum Weiter...")
        return

    com = ask_com_port()
    sec = ask_seconds("30")

    out = run_bash(SCRIPTS["bridge"], [com, cmd_num, sec])

    console.print("[green]Scan abgeschlossen[/green]")
    if out:
        console.print(out)

    log_path = extract_logfile_path(out or "")
    if not log_path or not log_path.exists() or log_path.is_dir():
        console.print("[red]Kein neues Log gefunden (Logfile: Zeile fehlt oder Pfad ungültig).[/red]")
        return

    _post_process_log(log_path, scan_type=f"cmd_{cmd_num}", com=com)


def run_target():
    if not _check_scripts_exist():
        console.input("\nENTER zum Weiter...")
        return

    com = ask_com_port()
    target_ip = console.input("Target IP (z.B. 192.168.2.10) > ").strip()
    if not target_ip:
        console.print("[red]Keine IP eingegeben.[/red]")
        return

    sec = ask_seconds("40")

    out = run_bash(SCRIPTS["target"], [com, target_ip, sec])
    if out:
        console.print(out)

    log_path = extract_logfile_path(out or "")
    if not log_path or not log_path.exists() or log_path.is_dir():
        console.print("[red]Kein neues Log gefunden (Logfile: Zeile fehlt oder Pfad ungültig).[/red]")
        return

    _post_process_log(log_path, scan_type="target_scan", com=com)


def run_summary():
    lf = pick_log()
    if not lf:
        return
    out = run_bash(SCRIPTS["summary"], [str(lf)])
    if out:
        console.print(out)


def run_profile_filter():
    prof = console.input("Profil (router/pc/server) > ").strip().lower()
    if prof not in ("router", "pc", "server"):
        console.print("[red]Profil ungültig.[/red]")
        return
    lf = pick_log()
    if not lf:
        return
    out = run_bash(SCRIPTS["profile_filter"], [prof, str(lf)])
    if out:
        console.print(out)


def run_auto_profile():
    lf = pick_log()
    if not lf:
        return
    out = run_bash(SCRIPTS["detect_profile"], [str(lf)])
    if out:
        console.print(out)


def run_report():
    ensure_dirs()

    console.print("[cyan]Report Generator (manuell)[/cyan]")
    console.print("1) Neueste Log automatisch")
    console.print("2) Log auswählen")
    ch = console.input("Auswahl > ").strip()

    if ch == "2":
        lf = pick_log()
        if not lf:
            return
        result = subprocess.run(
            ["python", str(SCRIPTS["report_gen"]), str(lf)],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        console.print((result.stdout or "") + (result.stderr or ""))
    else:
        result = subprocess.run(
            ["python", str(SCRIPTS["report_gen"])],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        console.print((result.stdout or "") + (result.stderr or ""))


def show_db_history():
    rows = last_scans(10)
    if not rows:
        console.print("[yellow]Keine Einträge in der Datenbank.[/yellow]")
        return

    table = Table(title="Scan History (letzte 10)")
    table.add_column("ID", style="cyan", width=4)
    table.add_column("Zeit", style="white")
    table.add_column("Profil", style="magenta", width=8)
    table.add_column("Gateway", style="green")
    table.add_column("Target", style="green")
    table.add_column("Ports", style="yellow")
    table.add_column("Logfile", style="dim")

    for row in rows:
        scan_id, created_at, profile, gateway, target, open_ports, logfile = row
        table.add_row(
            str(scan_id),
            created_at,
            profile or "-",
            gateway or "-",
            target or "-",
            open_ports or "-",
            logfile,
        )
    console.print(table)


def main():
    ensure_dirs()

    while True:
        console.clear()
        header()
        menu()
        choice = console.input("\nAuswahl > ").strip()

        if choice == "1":
            run_bridge("1")
        elif choice == "2":
            run_bridge("2")
        elif choice == "3":
            run_bridge("3")
        elif choice == "4":
            run_bridge("4")
        elif choice == "5":
            run_target()
        elif choice == "6":
            run_summary()
        elif choice == "7":
            run_profile_filter()
        elif choice == "8":
            run_auto_profile()
        elif choice == "9":
            files = list_latest_logs(10)
            show_logs_table(files)
        elif choice == "10":
            run_report()
        elif choice == "11":
            show_db_history()
        elif choice == "0":
            break
        else:
            console.print("[red]Ungültige Auswahl[/red]")

        console.input("\nENTER zum Weiter...")


if __name__ == "__main__":
    main()
