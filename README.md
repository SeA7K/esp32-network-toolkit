# ESP32 Network Toolkit

ESP32-gestütztes Werkzeug für WLAN-Übersicht, lokale Geräteerkennung und
TCP-Portprüfungen. Die Host-Werkzeuge sind Python- und Bash-Skripte.

## Dateien

Projektstruktur:

- `firmware/firmware.ino` — ESP32-Firmware
- `analysis/python_ui/` — Python-Oberfläche, Datenbank, Log-Auswertung und Berichte
- `host/bash/` — Bash-Steuerung und Log-Auswertung
- `host/powershell/esp32_serial.ps1` — serielle Verbindung unter Windows
- `profiles/` — Portlisten für die Profilfilter

## Voraussetzungen und Start

- ESP32 mit Arduino IDE oder Arduino CLI; Bibliotheken `WiFi`, `SPIFFS` und
  `ESPmDNS` kommen aus dem Arduino-ESP32-Core.
- Python 3.10 oder neuer sowie Git Bash und PowerShell unter Windows.
- Python-Pakete installieren: `python -m pip install -r requirements.txt`.
- `firmware/secrets.example.h` nach `firmware/secrets.h` kopieren, dort die
  WLAN-Zugangsdaten eintragen, Firmware hochladen und den seriellen Monitor
  schließen. `secrets.h` wird von Git ignoriert.
- Oberfläche starten: `python analysis/python_ui/app.py`.

Der direkte serielle Monitor kann mit
`python analysis/python_ui/serial_monitor.py --port COM3` gestartet werden.
`host/bash/main.sh` bietet das Bash-Menü.

## Lokale Dateien

Beim Betrieb entstehen `logs/`, `logs_normalized/`, `data/scans.db` und
`analysis/reports/`. Diese Dateien enthalten lokale Scan-Ergebnisse und werden
nicht eingecheckt. Portprofile liegen in `profiles/`.

## Scanbereich

Nur Geräte und Netze scannen, für die eine ausdrückliche Berechtigung besteht.
Ein manuell eingegebenes Ziel wird von der Firmware auf das aktuell verbundene
WLAN-Subnetz begrenzt. Die automatische LAN-Erkennung läuft nur in Subnetzen mit
höchstens 254 nutzbaren Geräteadressen; größere Netze werden abgewiesen.
Manuelle Zieladressen müssen zusätzlich private IPv4-Adressen sein.
