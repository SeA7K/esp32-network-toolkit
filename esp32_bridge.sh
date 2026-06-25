#!/usr/bin/env bash
# esp32_bridge.sh
# Windows (Git Bash) -> PowerShell -> ESP32
# Unterstützt ESP32 Menü: 1, 2, 3, 4

set -euo pipefail

# -----------------------------
# Parameter
# -----------------------------
PORT="${1:-COM3}"      # z.B. COM3
CMD="${2:-1}"          # 1=WLAN, 2=LAN, 3=Combo, 4=Gateway
SECONDS="${3:-30}"     # wie lange lesen

# -----------------------------
# Projekt-Root finden
# host/bash/esp32_bridge.sh  -> ProjektRoot = 2 Ebenen hoch
# -----------------------------
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

# -----------------------------
# PowerShell Script finden
# -----------------------------
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
  echo "Erwartet an einem dieser Orte:"
  for p in "${PS1_CANDIDATES[@]}"; do
    echo " - $p"
  done
  exit 1
fi

# -----------------------------
# Logfile im ProjektRoot/logs/
# -----------------------------
LOG_DIR="$PROJECT_ROOT/logs"
mkdir -p "$LOG_DIR"

TS="$(date +%Y-%m-%d_%H-%M-%S)"
OUTFILE="$LOG_DIR/esp32_${PORT}_${CMD}_${TS}.txt"

# -----------------------------
# Info
# -----------------------------
echo "[*] ESP32 Bridge"
echo "    Project:  $PROJECT_ROOT"
echo "    Port:     $PORT"
echo "    Command:  $CMD"
echo "    Seconds:  $SECONDS"
echo "    PS1:      $PS1_SCRIPT"
echo "    Logfile:  $OUTFILE"
echo

# -----------------------------
# PowerShell Bridge
# -----------------------------
# Git Bash / WSL -> Windows-Pfad umwandeln
# --- Pfade für PowerShell kompatibel machen (Git Bash) ---
to_winpath() {
  local p="$1"
  if command -v cygpath >/dev/null 2>&1; then
    cygpath -w "$p"
    return
  fi
  if command -v wslpath >/dev/null 2>&1; then
    wslpath -w "$p"
    return
  fi
  # letzter Fallback: gib den Pfad einfach so zurück
  echo "$p"
}

PS1_WIN_PATH="$(to_winpath "$PS1_SCRIPT")"
OUTFILE_WIN="$(to_winpath "$OUTFILE")"


powershell.exe -NoProfile -ExecutionPolicy Bypass \
  -File "$PS1_WIN_PATH" \
  -Port "$PORT" \
  -Command "$CMD" \
  -Seconds "$SECONDS" \
  -OutFile "$OUTFILE_WIN"
