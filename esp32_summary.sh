#!/usr/bin/env bash
# esp32_summary.sh
# Erstellt eine kompakte Zusammenfassung aus ESP32-Logs

set -euo pipefail

LOGFILE="${1:-}"

if [[ -z "$LOGFILE" || ! -f "$LOGFILE" ]]; then
  echo "[!] Bitte Logdatei angeben."
  echo "    Beispiel: ./esp32_summary.sh logs/esp32_COM3_4_*.txt"
  exit 1
fi

TARGET_IP=$(grep -Eo 'Gateway: [0-9.]+' "$LOGFILE" | awk '{print $2}' | head -n1)
OPEN_PORTS=$(grep 'OPEN:' "$LOGFILE" | awk '{print $2}' | tr '\n' ',' | sed 's/,$//')
COUNT=$(grep -c 'OPEN:' "$LOGFILE")

echo "======================"
echo "SUMMARY"
echo "======================"
[[ -n "$TARGET_IP" ]] && echo "Target: $TARGET_IP" || echo "Target: unbekannt"
echo "Open Ports: ${OPEN_PORTS:-keine}"
echo "Count: $COUNT"
echo "======================"
