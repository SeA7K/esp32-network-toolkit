from __future__ import annotations
import re
from datetime import datetime
from pathlib import Path
from db import insert_scan

BASE_DIR = Path(__file__).resolve().parents[1]
LOG_DIR = BASE_DIR / "logs_normalized"


def newest_log() -> Path | None:
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
    }

    for line in text.splitlines():
        if line.startswith("GATEWAY="):
            data["gateway"] = line.split("=", 1)[1].strip()
        elif line.startswith("HOST="):
            data["target"] = line.split("=", 1)[1].strip()
        elif line.startswith("OPEN_PORTS="):
            raw = line.split("=", 1)[1].strip()
            if raw and raw != "-":
                data["open_ports"] = [int(x) for x in raw.split(",") if x.strip().isdigit()]
        elif line.startswith("MDNS_FOUND="):
            v = line.split("=", 1)[1].strip()
            data["mdns_found"] = int(v) if v.isdigit() else None

    return data


def guess_profile(open_ports: list[int], gateway: str | None, target: str | None) -> str:
    # Minimal, aber stabil:
    if gateway and not target:
        return "router"
    if target:
        return "pc"
    if 22 in open_ports or 3389 in open_ports:
        return "server"
    return "unknown"


def import_log_to_db(log_path: Path) -> int:
    text = log_path.read_text(encoding="utf-8", errors="replace")
    parsed = parse_log(text)

    profile = guess_profile(parsed["open_ports"], parsed["gateway"], parsed["target"])
    ports_str = ",".join(map(str, parsed["open_ports"]))
    created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

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
