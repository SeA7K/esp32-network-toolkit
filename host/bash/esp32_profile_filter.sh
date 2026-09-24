#!/usr/bin/env bash
# esp32_profile_filter.sh
# Filtert OPEN-Ports aus einem ESP32-Log nach Profil (router/pc/server)

set -euo pipefail

PROFILE="${1:-}"
LOGFILE="${2:-}"

if [[ -z "$PROFILE" || -z "$LOGFILE" ]]; then
  echo "[!] Nutzung: ./esp32_profile_filter.sh <router|pc|server> <logfile>"
  echo "    Beispiel: ./esp32_profile_filter.sh router logs/esp32_COM3_4_*.txt"
  exit 1
fi

if [[ ! -f "$LOGFILE" ]]; then
  echo "[!] Logdatei nicht gefunden: $LOGFILE"
  exit 1
fi

case "$PROFILE" in
  router|pc|server) ;;
  *) echo "[!] Ungültiges Profil: $PROFILE"; exit 1 ;;
esac

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
PROFILE_FILE="$PROJECT_ROOT/profiles/${PROFILE}.txt"
if [[ ! -f "$PROFILE_FILE" ]]; then
  echo "[!] Profil nicht gefunden: $PROFILE_FILE"
  echo "    Verfügbare Profile:"
  ls -1 "$PROJECT_ROOT/profiles"/*.txt 2>/dev/null | sed 's#.*/##; s/\.txt$//' || true
  exit 1
fi

TARGET=$(grep -Eo 'Gateway: [0-9.]+' "$LOGFILE" | awk '{print $2}' | head -n1) || true
OPEN_ALL=$(grep -Eo 'OPEN: [0-9]+' "$LOGFILE" | awk '{print $2}' | sort -n | uniq) || true

echo "=============================="
echo "PROFILE FILTER"
echo "Profile: $PROFILE"
echo "Log:     $LOGFILE"
[[ -n "$TARGET" ]] && echo "Target:  $TARGET"
echo "=============================="

if [[ -z "$OPEN_ALL" ]]; then
  echo "Keine OPEN-Ports im Log gefunden."
  exit 0
fi

# Ports nach Profil matchen
MATCHED=$(echo "$OPEN_ALL" | grep -Fx -f <(sed 's/\r$//' "$PROFILE_FILE") || true)

if [[ -z "$MATCHED" ]]; then
  echo "Treffer: keine"
  exit 0
fi

COUNT=$(echo "$MATCHED" | wc -l | tr -d ' ')
PORTS=$(echo "$MATCHED" | tr '\n' ',' | sed 's/,$//')

echo "Treffer: $COUNT"
echo "Ports:   $PORTS"
echo "=============================="
