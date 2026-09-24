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

TARGET_IP=$(grep -Eo 'Gateway: [0-9.]+' "$LOGFILE" | awk '{print $2}' | head -n1) || true
OPEN_LINES=$(grep -Eo 'OPEN: [0-9]+' "$LOGFILE" || true)
if [[ -n "$OPEN_LINES" ]]; then
  OPEN_PORTS=$(printf '%s\n' "$OPEN_LINES" | awk '{print $2}' | sort -n -u | tr '\n' ',' | sed 's/,$//')
  COUNT=$(printf '%s\n' "$OPEN_PORTS" | tr ',' '\n' | awk 'NF { count++ } END { print count + 0 }')
else
  OPEN_PORTS=""
  COUNT=0
fi

echo "======================"
echo "SUMMARY"
echo "======================"
[[ -n "$TARGET_IP" ]] && echo "Target: $TARGET_IP" || echo "Target: unbekannt"
echo "Open Ports: ${OPEN_PORTS:-keine}"
echo "Count: $COUNT"
echo "======================"
