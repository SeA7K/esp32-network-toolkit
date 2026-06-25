from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import List, Tuple, Optional


def get_project_root() -> Path:
    """
    Findet den Projekt-Root, wo 'host/' und 'logs/' liegen.
    Funktioniert unabhängig vom Startpfad.
    """
    cur = Path(__file__).resolve()
    for _ in range(20):
        if (cur / "host").exists() and (cur / "logs").exists():
            return cur
        cur = cur.parent
    # Fallback: analysis/python_ui -> analysis -> ESP32_Terminal
    return Path(__file__).resolve().parents[2]


BASE_DIR = get_project_root()
DATA_DIR = BASE_DIR / "data"
DB_PATH = DATA_DIR / "scans.db"


def get_conn() -> sqlite3.Connection:
    """
    Öffnet eine SQLite-Verbindung mit WAL-Modus.
    """
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA foreign_keys=ON;")
    return conn


def init_db() -> None:
    """
    Legt die Tabelle 'scans' an, falls sie nicht existiert.
    """
    with get_conn() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS scans (
                id           INTEGER PRIMARY KEY AUTOINCREMENT,
                created_at   TEXT NOT NULL,
                logfile      TEXT NOT NULL,
                gateway      TEXT,
                target       TEXT,
                open_ports   TEXT,
                profile      TEXT,
                mdns_found   INTEGER
            )
            """
        )
        conn.execute("CREATE INDEX IF NOT EXISTS idx_scans_created_at ON scans(created_at)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_scans_profile ON scans(profile)")


def insert_scan(
    created_at: str,
    logfile: str,
    gateway: Optional[str],
    target: Optional[str],
    open_ports: str,
    profile: Optional[str],
    mdns_found: Optional[int],
) -> int:
    """
    Fügt einen neuen Scan in die DB ein.
    Gibt die Scan-ID zurück.
    """
    init_db()
    with get_conn() as conn:
        cur = conn.execute(
            """
            INSERT INTO scans (
                created_at,
                logfile,
                gateway,
                target,
                open_ports,
                profile,
                mdns_found
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (created_at, logfile, gateway, target, open_ports, profile, mdns_found),
        )
        return int(cur.lastrowid)


def last_scans(limit: int = 10) -> List[Tuple]:
    """
    Gibt die letzten Scans zurück (neuester zuerst).

    Rückgabe:
    (id, created_at, profile, gateway, target, open_ports, logfile)
    """
    init_db()
    with get_conn() as conn:
        cur = conn.execute(
            """
            SELECT
                id,
                created_at,
                profile,
                gateway,
                target,
                open_ports,
                logfile
            FROM scans
            ORDER BY id DESC
            LIMIT ?
            """,
            (limit,),
        )
        return cur.fetchall()
