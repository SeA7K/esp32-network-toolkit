#!/usr/bin/env bash
# esp32_detect_profile.sh
# Erkennt automatisch ein Profil (router/pc/server/unknown) anhand der offenen Ports im ESP32-Log.

set -euo pipefail

LOGFILE="${1:-}"

if [[ -z "$LOGFILE" || ! -f "$LOGFILE" ]]; then
  echo "[!] Nutzung: ./esp32_detect_profile.sh <logfile>"
  echo "    Beispiel: ./esp32_detect_profile.sh logs/esp32_COM3_4_*.txt"
  exit 1
fi

# offene Ports aus Log holen (einmalig/sortiert)
OPEN_PORTS="$(grep -Eo 'OPEN: [0-9]+' "$LOGFILE" | awk '{print $2}' | sort -n | uniq || true)"

if [[ -z "$OPEN_PORTS" ]]; then
  echo "=============================="
  echo "AUTO PROFILE"
  echo "=============================="
  echo "Log: $LOGFILE"
  echo "Keine OPEN-Ports gefunden."
  echo "Ergebnis: unknown"
  echo "=============================="
  exit 0
fi

# Helper: check ob ein Port in OPEN_PORTS enthalten ist
has_port() {
  local p="$1"
  echo "$OPEN_PORTS" | grep -qx "$p"
}

# Scoring-System (Heuristik)
router_score=0
pc_score=0
server_score=0

# ---------- Router Heuristik ----------
# DNS/HTTP/HTTPS typisch für Router-WebUI
has_port 53  && router_score=$((router_score+3))
has_port 80  && router_score=$((router_score+2))
has_port 443 && router_score=$((router_score+2))

# ---------- Windows-PC Heuristik ----------
# SMB/RPC/RDP typisch für Windows
has_port 135  && pc_score=$((pc_score+3))
has_port 139  && pc_score=$((pc_score+3))
has_port 445  && pc_score=$((pc_score+4))
has_port 3389 && pc_score=$((pc_score+3))

# ---------- Server Heuristik ----------
# SSH + Web + App-Ports typisch für Server
has_port 22   && server_score=$((server_score+3))
has_port 80   && server_score=$((server_score+2))
has_port 443  && server_score=$((server_score+2))
has_port 8080 && server_score=$((server_score+2))
has_port 3306 && server_score=$((server_score+2))
has_port 5432 && server_score=$((server_score+2))

# ---------- Entscheidung ----------
best="unknown"
best_score=0

if (( router_score > best_score )); then best="router"; best_score=$router_score; fi
if (( pc_score > best_score )); then best="pc"; best_score=$pc_score; fi
if (( server_score > best_score )); then best="server"; best_score=$server_score; fi

# Wenn Score zu niedrig -> unknown
if (( best_score < 3 )); then
  best="unknown"
fi

TARGET="$(grep -Eo 'Gateway: [0-9.]+' "$LOGFILE" | awk '{print $2}' | head -n1)"

echo "=============================="
echo "AUTO PROFILE"
echo "=============================="
echo "Log:    $LOGFILE"
[[ -n "$TARGET" ]] && echo "Target: $TARGET"
echo "Open:   $(echo "$OPEN_PORTS" | tr '\n' ',' | sed 's/,$//')"
echo "------------------------------"
echo "Scores: router=$router_score | pc=$pc_score | server=$server_score"
echo "Ergebnis: $best"
echo "=============================="
