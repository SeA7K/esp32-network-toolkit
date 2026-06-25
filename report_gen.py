#!/usr/bin/env python3
from __future__ import annotations

import argparse
import re
from datetime import datetime
from pathlib import Path

# Projekt-Root: .../ESP32_Terminal
# report_gen.py liegt in: ESP32_Terminal/analysis/python_ui/report_gen.py
BASE_DIR = Path(__file__).resolve().parents[2]

LOG_DIR = BASE_DIR / "logs"
REPORT_DIR = BASE_DIR / "analysis" / "reports"


def newest_log() -> Path | None:
    """Nimmt das neueste .txt Log aus /logs."""
    if not LOG_DIR.exists():
        return None
    files = sorted(LOG_DIR.glob("*.txt"), key=lambda p: p.stat().st_mtime, reverse=True)
    return files[0] if files else None


def parse_log(text: str) -> dict:
    data = {
        "gateway": None,
        "target": None,
        "open_ports": [],
        "mdns_found": None,
        "raw_open_lines": [],
    }

    # Gateway
    m = re.search(r"Gateway:\s*([0-9]+\.[0-9]+\.[0-9]+\.[0-9]+)", text)
    if m:
        data["gateway"] = m.group(1)

    # Target (manueller Scan)
    m = re.search(r"Target:\s*([0-9]+\.[0-9]+\.[0-9]+\.[0-9]+)", text)
    if m:
        data["target"] = m.group(1)

    # mDNS count
    m = re.search(r"mDNS.*gefunden:\s*(\d+)", text)
    if m:
        data["mdns_found"] = int(m.group(1))

    # OPEN lines + ports
    for line in text.splitlines():
        if "OPEN:" in line:
            data["raw_open_lines"].append(line.strip())
            pm = re.search(r"OPEN:\s*(\d+)", line)
            if pm:
                port = int(pm.group(1))
                if port not in data["open_ports"]:
                    data["open_ports"].append(port)

    data["open_ports"].sort()
    return data


def risk_rating(open_ports: list[int]) -> tuple[str, list[str]]:
    """Simple regelbasierte Bewertung (read-only)."""
    notes: list[str] = []
    risk = "LOW"

    if 80 in open_ports and 443 not in open_ports:
        risk = "MEDIUM"
        notes.append("HTTP (80) offen, aber kein HTTPS (443) erkannt → Admin-UI könnte unverschlüsselt sein.")
    if 443 in open_ports:
        notes.append("HTTPS (443) offen → verschlüsselte Verwaltung möglich (gut).")
    if 53 in open_ports:
        notes.append("DNS (53) offen → normal im LAN (typisch Router).")

    if len(open_ports) >= 5:
        risk = "MEDIUM"
        notes.append("Viele offene Ports im Scan → größere Angriffsfläche.")

    return risk, notes


def guess_scope(data: dict) -> str:
    if data.get("target"):
        return f"Target-IP Scan gegen {data['target']} (autorisiert, eigenes Netz)."
    if data.get("gateway"):
        return f"Router/Gateway Scan gegen {data['gateway']} (autorisiert, eigenes Netz)."
    return "Unbekannter Scope (Log enthält keine Target/Gateway-Zeile)."


def build_report(log_path: Path, parsed: dict) -> str:
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    ports = parsed["open_ports"]
    risk, notes = risk_rating(ports)

    lines: list[str] = []
    lines.append("# ESP32 Network Toolkit – Scan Report")
    lines.append("")
    lines.append(f"**Datum:** {ts}")
    lines.append(f"**Logfile:** `{log_path.name}`")
    lines.append("")
    lines.append("## Scope")
    lines.append(guess_scope(parsed))
    lines.append("")
    lines.append("## Ergebnisse (Kurz)")
    lines.append(f"- Gateway: `{parsed['gateway'] or 'unbekannt'}`")
    lines.append(f"- Target: `{parsed['target'] or '—'}`")
    lines.append(f"- Offene Ports: `{', '.join(map(str, ports)) if ports else 'keine gefunden'}`")
    lines.append(f"- mDNS Geräte gefunden: `{parsed['mdns_found'] if parsed['mdns_found'] is not None else 'unbekannt'}`")
    lines.append("")
    lines.append("## Risiko-Bewertung")
    lines.append(f"**Risk:** `{risk}`")
    lines.append("")
    if notes:
        lines.append("**Findings:**")
        for n in notes:
            lines.append(f"- {n}")
    else:
        lines.append("- Keine besonderen Findings aus den Regeln ableitbar.")
    lines.append("")
    lines.append("## Evidence (Auszug)")
    if parsed["raw_open_lines"]:
        lines.append("```txt")
        lines.extend(parsed["raw_open_lines"])
        lines.append("```")
    else:
        lines.append("_Keine OPEN:-Zeilen im Log gefunden._")
    lines.append("")
    lines.append("## Empfehlungen (Hardening)")
    lines.append("- Router-Adminzugriff nur im LAN erlauben; Remote-Management deaktiviert lassen.")
    lines.append("- Wenn möglich: HTTPS für Router-UI aktivieren/erzwingen (HTTP vermeiden).")
    lines.append("- UPnP/WPS nur wenn nötig aktiv; sonst deaktivieren.")
    lines.append("- Firmware aktuell halten und Konfiguration dokumentieren.")
    lines.append("")
    lines.append("## Reproduzierbarkeit")
    lines.append("1. ESP32 mit dem Netzwerk verbinden.")
    lines.append("2. Scan starten (Router/Gateway oder Target-IP).")
    lines.append("3. Log speichern und Report neu generieren.")
    lines.append("")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate Markdown report from ESP32 log")
    parser.add_argument("logfile", nargs="?", default="", help="Pfad zur Logdatei (optional)")
    args = parser.parse_args()

    # Reports-Ordner anlegen
    REPORT_DIR.mkdir(parents=True, exist_ok=True)

    # Log bestimmen
    if args.logfile.strip():
        log_path = Path(args.logfile).expanduser()
    else:
        log_path = newest_log()

    # --- SAFE GUARD: Log muss existieren und eine Datei sein ---
    if log_path is None:
        print("[ERROR] Kein Log gefunden in:", LOG_DIR)
        print("Tipp: Starte erst einen Scan oder gib ein Log an, z.B.:")
        print(r"python report_gen.py ..\..\logs\esp32_COM3_....txt")
        return 1

    log_path = Path(str(log_path)).expanduser()

    if not str(log_path).strip():
        print("[ERROR] Kein Log ausgewählt (leer).")
        return 1

    if not log_path.exists():
        print(f"[ERROR] Log existiert nicht: {log_path}")
        return 1

    if log_path.is_dir():
        print(f"[ERROR] Log-Pfad ist ein Ordner, keine Datei: {log_path}")
        return 1
    # --- SAFE GUARD ENDE ---

    # Lesen + Report bauen
    text = log_path.read_text(encoding="utf-8", errors="replace")
    parsed = parse_log(text)

    out_name = f"report_{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}.md"
    out_path = REPORT_DIR / out_name
    out_path.write_text(build_report(log_path, parsed), encoding="utf-8")

    print(f"[OK] Report erstellt: {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
