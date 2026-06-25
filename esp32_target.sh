#!/usr/bin/env bash
# esp32_target.sh
# Windows (Git Bash) -> PowerShell -> ESP32 Menüpunkt 5 + IP senden

set -euo pipefail

PORT="${1:-COM3}"
TARGET="${2:-}"
SECONDS="${3:-35}"

if [[ -z "$TARGET" ]]; then
  echo "[!] Nutzung: bash host/bash/esp32_target.sh COM3 192.168.2.10 35"
  exit 1
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

PS1_CANDIDATES=(
  "$PROJECT_ROOT/host/powershell/esp32_serial.ps1"
  "$PROJECT_ROOT/host/esp32_serial.ps1"
  "$PROJECT_ROOT/esp32_serial.ps1"
)

PS1_SCRIPT=""
for p in "${PS1_CANDIDATES[@]}"; do
  if [[ -f "$p" ]]; then
    PS1_SCRIPT="$p"
    break
  fi
done

if [[ -z "$PS1_SCRIPT" ]]; then
  echo "[ERROR] esp32_serial.ps1 nicht gefunden."
  for p in "${PS1_CANDIDATES[@]}"; do
    echo " - $p"
  done
  exit 1
fi

LOG_DIR="$PROJECT_ROOT/logs"
mkdir -p "$LOG_DIR"

TS="$(date +%Y-%m-%d_%H-%M-%S)"
OUTFILE="$LOG_DIR/esp32_${PORT}_target_${TARGET}_${TS}.txt"

echo "[*] ESP32 Target Scan"
echo "    Project:  $PROJECT_ROOT"
echo "    Port:     $PORT"
echo "    Target:   $TARGET"
echo "    Seconds:  $SECONDS"
echo "    PS1:      $PS1_SCRIPT"
echo "    Logfile:  $OUTFILE"
echo

powershell.exe -NoProfile -ExecutionPolicy Bypass \
  -File "$PS1_SCRIPT" \
  -Port "$PORT" \
  -Command "5" \
  -Arg "$TARGET" \
  -Seconds "$SECONDS" \
  -OutFile "$OUTFILE"

echo
echo "[+] Fertig. Log gespeichert:"
echo "    $OUTFILE"
