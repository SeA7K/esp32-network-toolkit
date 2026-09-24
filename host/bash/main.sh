#!/usr/bin/env bash
# main.sh
# Hauptmenü für ESP32 Toolkit (Windows Git Bash -> PowerShell -> ESP32)

set -euo pipefail

# Basis-Pfade (absolut)
BASE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ESP32_DIR="$BASE_DIR"
PROJECT_ROOT="$(cd "$BASE_DIR/../.." && pwd)"
LOG_DIR="$PROJECT_ROOT/logs"

pause() {
  read -r -p "Weiter mit ENTER..."
}

esp32_menu() {
  while true; do
    clear
    echo "=============================="
    echo "ESP32 TOOLKIT (Windows Bridge)"
    echo "=============================="
    echo "[1] WLAN Scan (ESP32)"
    echo "[2] LAN Discovery (ESP32)"
    echo "[3] Combo Scan (ESP32)"
    echo "[4] Router/Gateway Scan (ESP32)"
    echo "[5] Target-IP Scan (ESP32)"
    echo "------------------------------"
    echo "[6] Summary aus Log erstellen"
    echo "[7] Profile Filter (router/pc/server)"
    echo "[8] Auto Profile (erkennen)"
    echo "------------------------------"
    echo "[0] Zurück"
    echo "=============================="
    echo
    read -r -p "Auswahl: " CH

    case "$CH" in
      1|2|3|4)
        read -r -p "COM Port (z.B. COM3): " COM
        COM="${COM:-COM3}"
        read -r -p "Sekunden lesen (z.B. 30): " SEC
        SEC="${SEC:-30}"

        "$ESP32_DIR/esp32_bridge.sh" "$COM" "$CH" "$SEC"

        echo
        echo "Letzte Logs:"
        ls -1t "$LOG_DIR" 2>/dev/null | head -n 5 || true
        pause
        ;;

      5)
        read -r -p "COM Port (z.B. COM3): " COM
        COM="${COM:-COM3}"
        read -r -p "Target-IP (z.B. 192.168.2.10): " TIP
        read -r -p "Sekunden lesen (z.B. 40): " SEC
        SEC="${SEC:-40}"

        "$ESP32_DIR/esp32_target.sh" "$COM" "$TIP" "$SEC"

        echo
        echo "Letzte Logs:"
        ls -1t "$LOG_DIR" 2>/dev/null | head -n 5 || true
        pause
        ;;

      6)
        read -r -p "Logfile (z.B. logs/esp32_...txt): " LF
        if [[ -z "$LF" ]]; then
          echo "[!] Kein Logfile angegeben."
          pause
          continue
        fi

        LOG_PATH="$PROJECT_ROOT/$LF"
        if [[ ! -f "$LOG_PATH" ]]; then
          echo "[!] Logdatei nicht gefunden: $LOG_PATH"
          pause
          continue
        fi

        "$ESP32_DIR/esp32_summary.sh" "$LOG_PATH"
        pause
        ;;

      7)
        read -r -p "Profil (router|pc|server): " PROF
        read -r -p "Logfile (z.B. logs/esp32_...txt): " LF
        if [[ -z "$PROF" || -z "$LF" ]]; then
          echo "[!] Profil oder Logfile fehlt."
          pause
          continue
        fi

        LOG_PATH="$PROJECT_ROOT/$LF"
        if [[ ! -f "$LOG_PATH" ]]; then
          echo "[!] Logdatei nicht gefunden: $LOG_PATH"
          pause
          continue
        fi

        "$ESP32_DIR/esp32_profile_filter.sh" "$PROF" "$LOG_PATH"
        pause
        ;;

      8)
        read -r -p "Logfile (z.B. logs/esp32_...txt): " LF
        if [[ -z "$LF" ]]; then
          echo "[!] Kein Logfile angegeben."
          pause
          continue
        fi

        # 🔧 WICHTIG: relativen Pfad sicher auf absolut auflösen
        LOG_PATH="$PROJECT_ROOT/$LF"

        if [[ ! -f "$LOG_PATH" ]]; then
          echo "[!] Logdatei nicht gefunden: $LOG_PATH"
          pause
          continue
        fi

        "$ESP32_DIR/esp32_detect_profile.sh" "$LOG_PATH"
        pause
        ;;

      0)
        return
        ;;

      *)
        echo "Ungültige Auswahl."
        pause
        ;;
    esac
  done
}

# Hauptmenü
while true; do
  clear
  echo "=============================="
  echo "HAUPTMENÜ"
  echo "=============================="
  echo "[1] ESP32 Toolkit"
  echo "[0] Beenden"
  echo "=============================="
  echo
  read -r -p "Auswahl: " MAIN

  case "$MAIN" in
    1) esp32_menu ;;
    0) exit 0 ;;
    *) echo "Ungültige Auswahl."; pause ;;
  esac
done
