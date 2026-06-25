ESP32 Network Toolkit

ESP32-basierter Netzwerkscanner mit Python-Analyse und Bash-Steuerung.

Features
- WLAN Scan (Netzwerke in Reichweite)
- LAN Discovery (aktive Geräte finden)
- Port Scan (TCP)
- mDNS Namensauflösung
- Geräteprofil-Erkennung (Router, PC, Server)
- Automatische Markdown-Reports
- Python Terminal UI

Struktur
- /firmware → Arduino Code (ESP32)
- /host/bash → Bash Steuerungsskripte
- /host/powershell → PowerShell Serial Monitor
- /analysis/python_ui → Python Analyse & UI
- /profiles → Geräteprofile

Setup
Folgende Dateien/Ordner werden lokal generiert:
- logs/ → wird automatisch erstellt
- data/scans.db → wird automatisch erstellt
- analysis/reports/ → werden automatisch generiert

In der Firmware SSID und Passwort eintragen:
const char* WIFI_SSID = "DEIN_NETZWERK";
const char* WIFI_PASS = "DEIN_PASSWORT";

Hinweis
Nur im eigenen Netzwerk verwenden.
Defensives Lernprojekt — keine Exploits.
