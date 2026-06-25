#!/usr/bin/env python3
"""
serial_monitor.py
ESP32 Live Serial Monitor (Windows / Git Bash / Python)

Features:
- Live-Ausgabe vom ESP32
- farbige Hervorhebung (OPEN / ERROR / WARN)
- Logging in logs/serial_*.txt
- optional: sendet eine Zeile (z.B. "m" fürs Menü) beim Start
"""

from __future__ import annotations

import argparse
import sys
import time
from datetime import datetime
from pathlib import Path

import serial
from serial.tools import list_ports

from rich.console import Console
from rich.panel import Panel

console = Console()

def list_com_ports() -> list[str]:
    ports = []
    for p in list_ports.comports():
        # p.device z.B. "COM3"
        ports.append(p.device)
    return ports

def style_line(line: str) -> str:
    s = line.rstrip("\r\n")

    # Menü-Zeilen (z.B. "[1] ...", "[l] ...") einheitlich färben
    if s.startswith("[") and "]" in s[:4]:
        return f"[cyan]{s}[/]"

    # Treffer hervorheben
    if "OPEN:" in s or " OPEN " in s:
        return f"[bold green]{s}[/]"

    # Fehler hervorheben
    if "ERROR" in s or "Fehler" in s or "Zugriff" in s:
        return f"[bold red]{s}[/]"

    # Warnungen
    if "WARN" in s or "Achtung" in s:
        return f"[yellow]{s}[/]"

    return s


def ensure_logs_dir(base_dir: Path) -> Path:
    log_dir = base_dir / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    return log_dir

def open_serial(port: str, baud: int, timeout: float) -> serial.Serial:
    # pyserial unter Windows: port="COM3" ist korrekt
    return serial.Serial(port=port, baudrate=baud, timeout=timeout)

def main() -> int:
    parser = argparse.ArgumentParser(description="ESP32 Live Serial Monitor (pyserial + rich)")
    parser.add_argument("--port", default="", help='COM Port, z.B. "COM3"')
    parser.add_argument("--baud", type=int, default=115200, help="Baudrate (Default 115200)")
    parser.add_argument("--seconds", type=int, default=0, help="Laufzeit in Sekunden (0 = unendlich)")
    parser.add_argument("--send", default="", help='Optional: beim Start eine Zeile senden (z.B. "m")')
    parser.add_argument("--log", default="", help="Optional: Log-Datei (sonst automatisch)")
    args = parser.parse_args()

    # Base: .../ESP32_Terminal
    base_dir = Path(__file__).resolve().parents[1]
    log_dir = ensure_logs_dir(base_dir)

    ports = list_com_ports()
    if not args.port:
        if not ports:
            console.print("[red]Kein COM-Port gefunden. ESP32 eingesteckt?[/red]")
            return 1
        # nimm den ersten gefundenen
        args.port = ports[0]

    # Logfile
    if args.log:
        logfile = Path(args.log)
    else:
        ts = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        logfile = log_dir / f"serial_{args.port}_{ts}.txt"

    console.print(Panel(
        f"[bold cyan]ESP32 Live Serial Monitor[/]\n"
        f"Port: [bold]{args.port}[/]\n"
        f"Baud: [bold]{args.baud}[/]\n"
        f"Log:  [bold]{logfile}[/]\n"
        f"Ports gefunden: {', '.join(ports) if ports else '(keine)'}\n\n"
        f"[dim]Hinweis: Arduino Serial Monitor muss geschlossen sein.[/dim]\n"
        f"[dim]Beenden: Strg + C[/dim]",
        title="Start",
        border_style="cyan"
    ))

    try:
        ser = open_serial(args.port, args.baud, timeout=0.2)
    except Exception as e:
        console.print(f"[bold red]Konnte Port nicht öffnen: {e}[/bold red]")
        console.print("[yellow]Typische Ursache: COM ist bereits offen (Arduino Serial Monitor/IDE schließen).[/yellow]")
        return 2

    # optional etwas senden (z.B. "m" -> Menü anzeigen)
    if args.send.strip():
        try:
            time.sleep(0.4)
            ser.write((args.send.strip() + "\n").encode("utf-8", errors="ignore"))
        except Exception:
            pass

    start = time.time()
    lines_written = 0

    try:
        with open(logfile, "w", encoding="utf-8") as f:
            while True:
                if args.seconds > 0 and (time.time() - start) >= args.seconds:
                    console.print("[yellow]Zeitlimit erreicht – stoppe.[/yellow]")
                    break

                try:
                    raw = ser.readline()
                except Exception as e:
                    console.print(f"[bold red]Read-Fehler: {e}[/bold red]")
                    break

                if not raw:
                    continue

                try:
                    line = raw.decode("utf-8", errors="replace")
                except Exception:
                    line = str(raw)

                # Ausgabe im Terminal (farbig)
                console.print(style_line(line))

                # in Datei schreiben (ohne rich tags)
                f.write(line)
                lines_written += 1

    except KeyboardInterrupt:
        console.print("\n[cyan]Stop (Strg+C).[/cyan]")
    finally:
        try:
            ser.close()
        except Exception:
            pass

    console.print(Panel(
        f"[green]Fertig[/green]\n"
        f"Zeilen: {lines_written}\n"
        f"Log gespeichert: {logfile}",
        title="Done",
        border_style="green"
    ))
    return 0

if __name__ == "__main__":
    sys.exit(main())
