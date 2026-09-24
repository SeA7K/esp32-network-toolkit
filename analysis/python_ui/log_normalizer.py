from __future__ import annotations
import re
from datetime import datetime
from ipaddress import IPv4Address, AddressValueError
from pathlib import Path


def extract_ports(text: str) -> list[int]:
    ports = set()

    for m in re.finditer(r"OPEN:\s*(\d+)", text):
        port = int(m.group(1))
        if 1 <= port <= 65535:
            ports.add(port)

    m = re.search(r"(OPEN_PORTS|Open\s*Ports)\s*[:=]\s*([0-9,\s]+)", text, re.IGNORECASE)
    if m:
        for p in m.group(2).replace(" ", "").split(","):
            if p.isdigit() and 1 <= int(p) <= 65535:
                ports.add(int(p))

    return sorted(ports)


def extract_ip(label: str, text: str) -> str | None:
    m = re.search(
        rf"{label}\s*[:=]\s*([0-9]+\.[0-9]+\.[0-9]+\.[0-9]+)",
        text,
        re.IGNORECASE,
    )
    if not m:
        return None
    try:
        return str(IPv4Address(m.group(1)))
    except AddressValueError:
        return None


def extract_mdns(text: str) -> int | None:
    m = re.search(r"mDNS.*?(gefunden|found)\s*[:=]\s*(\d+)", text, re.IGNORECASE)
    return int(m.group(2)) if m else None


def normalize_log(raw_text: str, scan_type: str, com: str | None = None) -> str:
    ports = extract_ports(raw_text)
    gateway = extract_ip("Gateway", raw_text)
    target = extract_ip("Target", raw_text) or extract_ip("HOST", raw_text)
    mdns = extract_mdns(raw_text)

    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    ports_str = ",".join(map(str, ports)) if ports else "-"

    lines = []
    lines.append("[SCAN]")
    lines.append(f"TYPE={scan_type}")
    lines.append(f"TIME={now}")
    lines.append("DEVICE=ESP32")
    if com:
        lines.append(f"COM={com}")
    lines.append("")
    lines.append("[NETWORK]")
    lines.append(f"GATEWAY={gateway or '-'}")
    lines.append("")
    lines.append("[RESULT]")
    lines.append(f"HOST={target or '-'}")
    lines.append(f"OPEN_PORTS={ports_str}")
    lines.append(f"MDNS_FOUND={mdns if mdns is not None else '-'}")
    lines.append("")
    lines.append("[RAW]")
    lines.append(raw_text.strip())

    return "\n".join(lines) + "\n"


def write_normalized(in_log: Path, out_log: Path, scan_type: str, com: str | None = None):
    raw = in_log.read_text(encoding="utf-8", errors="replace")
    normalized = normalize_log(raw, scan_type=scan_type, com=com)
    out_log.write_text(normalized, encoding="utf-8")
