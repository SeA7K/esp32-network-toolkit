from __future__ import annotations

import argparse
import re
from datetime import datetime
from pathlib import Path

from db import insert_scan


def _first_ip(text: str) -> str | None:
    m = re.search(r"(\d{1,3}(?:\.\d{1,3}){3})", text)
    return m.group(1) if m else None


def parse_log(text: str) -> dict:
    """
    Unterstützt:
    - Normalized Logs (STUFE 2): GATEWAY=..., HOST=..., OPEN_PORTS=..., MDNS_FOUND=...
    - Alte RAW Logs (Fallback):  Gateway: ..., Target: ..., OPEN: 80, mDNS ... gefunden: 3
    """
    data = {
        "gateway": None,
        "target": None,
        "open_ports": [],
        "mdns_found": None,
    }

    # -----------------------
    # 1) Normalized Format
    # -----------------------
    m = re.search(r"^\s*GATEWAY\s*=\s*(.+)\s*$", text, re.IGNORECASE | re.MULTILINE)
    if m:
        data["gateway"] = _first_ip(m.group(1))

    m = re.search(r"^\s*HOST\s*=\s*(.+)\s*$", text, re.IGNORECASE | re.MULTILINE)
    if m:
        data["target"] = _first_ip(m.group(1))

    m = re.search(r"^\s*OPEN_PORTS\s*=\s*([0-9,\s-]*)\s*$", text, re.IGNORECASE | re.MULTILINE)
    if m:
        raw = m.group(1).strip()
        if raw and raw != "-":
            ports = []
            for p in raw.replace(" ", "").split(","):
                if p.isdigit():
                    ports.append(int(p))
            data["open_ports"] = sorted(set(ports))

    m = re.search(r"^\s*MDNS_FOUND\s*=\s*(\d+)\s*$", text, re.IGNORECASE | re.MULTILINE)
    if m:
        data["mdns_found"] = int(m.group(1))

    # Wenn normalized gefunden wurde → fertig
    if data["gateway"] or data["target"] or data["open_ports"] or data["mdns_found"] is not None:
        return data

    # -----------------------
    # 2) RAW Fallback
    # -----------------------
    m = re.search(r"Gateway:\s*([0-9]+\.[0-9]+\.[0-9]+\.[0-9]+)", text)
    if m:
        data["gateway"] = m.group(1)

    m = re.search(r"Target:\s*([0-9]+\.[0-9]+\.[0-9]+\.[0-9]+)", text)
    if m:
        data["target"] = m.group(1)

    m = re.search(r"mDNS.*gefunden:\s*(\d+)", text)
    if m:
        data["mdns_found"] = int(m.group(1))

    ports = set()
    for line in text.splitlines():
        # Beispiele: "OPEN: 80" oder "OPEN:80"
        pm = re.search(r"OPEN:\s*(\d+)", line)
        if pm:
            ports.add(int(pm.group(1)))

    data["open_ports"] = sorted(ports)
    return data


def guess_profile(open_ports: list[int], gateway_present: bool, target_present: bool) -> str:
    # simple Heuristik
    if gateway_present and not target_present:
        return "router"
    if 22 in open_ports or 3389 in open_ports:
        return "server"
    if target_present:
        return "pc"
    return "unknown"


def import_log_to_db(log_path: Path) -> int:
    """
    Wird von app.py direkt aufgerufen.
    """
    text = log_path.read_text(encoding="utf-8", errors="replace")
    parsed = parse_log(text)

    profile = guess_profile(
        parsed["open_ports"],
        gateway_present=parsed["gateway"] is not None,
        target_present=parsed["target"] is not None,
    )

    created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    ports_str = ",".join(map(str, parsed["open_ports"]))

    scan_id = insert_scan(
        created_at=created_at,
        logfile=log_path.name,
        gateway=parsed["gateway"],
        target=parsed["target"],
        open_ports=ports_str,
        profile=profile,
        mdns_found=parsed["mdns_found"],
    )
    return scan_id


def main():
    parser = argparse.ArgumentParser(description="Import ESP32 log into SQLite DB")
    parser.add_argument("logfile", help="Pfad zur Logdatei")
    args = parser.parse_args()

    log_path = Path(args.logfile)
    if not log_path.exists():
        print("[ERROR] Logfile nicht gefunden.")
        return

    scan_id = import_log_to_db(log_path)
    print(f"[OK] In DB gespeichert. ID={scan_id}")


if __name__ == "__main__":
    main()
