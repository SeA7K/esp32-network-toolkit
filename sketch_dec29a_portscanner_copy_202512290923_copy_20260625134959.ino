#include <WiFi.h>
#include <SPIFFS.h>
#include <ESPmDNS.h>

// =====================
// CONFIG (HIER ANPASSEN)
// =====================
const char* WIFI_SSID = "WLAN NETZWERK";
const char* WIFI_PASS = "PASSWORT";

// Discovery-Ports: schneller "lebt"-Check
const uint16_t DISCOVERY_PORTS[] = { 80, 443, 22, 53, 445, 139 };
const int DISCOVERY_PORTS_COUNT = sizeof(DISCOVERY_PORTS) / sizeof(DISCOVERY_PORTS[0]);

// Portscan-Liste: Standardports
const uint16_t SCAN_PORTS[] = { 21, 22, 23, 53, 80, 110, 139, 143, 443, 445, 3389 };
const int SCAN_PORTS_COUNT = sizeof(SCAN_PORTS) / sizeof(SCAN_PORTS[0]);

// Timeouts (ms)
const uint16_t CONNECT_TIMEOUT_MS = 120;
const uint16_t WIFI_CONNECT_TIMEOUT_MS = 12000;

// Logging
const char* LOG_FILE = "/scan_log.txt";

// mDNS Services, nach denen wir suchen
struct MdnsService { const char* service; const char* proto; };
MdnsService MDNS_SERVICES[] = {
  { "workstation", "tcp" },
  { "http", "tcp" },
  { "ssh", "tcp" },
  { "smb", "tcp" },
  { "printer", "tcp" },
  { "ipp", "tcp" }
};
const int MDNS_SERVICE_COUNT = sizeof(MDNS_SERVICES) / sizeof(MDNS_SERVICES[0]);

// IP -> Hostname Mapping (mDNS)
struct HostMapEntry {
  IPAddress ip;
  String hostname;
};
HostMapEntry hostMap[30];
int hostMapCount = 0;

unsigned long lastMenuPrint = 0;

// ========== Utils ==========
String encTypeName(wifi_auth_mode_t e) {
  switch (e) {
    case WIFI_AUTH_OPEN: return "OPEN";
    case WIFI_AUTH_WEP: return "WEP";
    case WIFI_AUTH_WPA_PSK: return "WPA";
    case WIFI_AUTH_WPA2_PSK: return "WPA2";
    case WIFI_AUTH_WPA_WPA2_PSK: return "WPA/WPA2";
    case WIFI_AUTH_WPA2_ENTERPRISE: return "WPA2-ENT";
    case WIFI_AUTH_WPA3_PSK: return "WPA3";
    case WIFI_AUTH_WPA2_WPA3_PSK: return "WPA2/WPA3";
    default: return "UNKNOWN";
  }
}

String ipToString(const IPAddress& ip) {
  return String(ip[0]) + "." + String(ip[1]) + "." + String(ip[2]) + "." + String(ip[3]);
}

IPAddress networkBase(IPAddress ip, IPAddress mask) {
  return IPAddress(ip[0] & mask[0], ip[1] & mask[1], ip[2] & mask[2], ip[3] & mask[3]);
}

// ========== SPIFFS / Logging ==========
bool initFS() {
  if (!SPIFFS.begin(true)) {
    Serial.println("[FS] SPIFFS mount fehlgeschlagen ❌");
    return false;
  }
  Serial.println("[FS] SPIFFS bereit ✅");
  return true;
}

void logLine(const String& line) {
  File f = SPIFFS.open(LOG_FILE, FILE_APPEND);
  if (!f) return;
  String out = "[" + String(millis()) + "ms] " + line + "\n";
  f.print(out);
  f.close();
}

void logHeader(const String& title) {
  logLine("--------------------------------------------------");
  logLine(title);
  logLine("--------------------------------------------------");
}

void showLog() {
  Serial.println("\n[LOG] Inhalt:");
  if (!SPIFFS.exists(LOG_FILE)) {
    Serial.println("Noch kein Log vorhanden.");
    return;
  }
  File f = SPIFFS.open(LOG_FILE, FILE_READ);
  if (!f) {
    Serial.println("Log konnte nicht gelesen werden.");
    return;
  }
  while (f.available()) {
    Serial.write(f.read());
  }
  f.close();
  Serial.println("\n[LOG] Ende.");
}

void clearLog() {
  if (SPIFFS.exists(LOG_FILE)) SPIFFS.remove(LOG_FILE);
  Serial.println("[LOG] Log gelöscht ✅");
}

// ========== WiFi Connect ==========
bool ensureWiFiConnected() {
  if (WiFi.status() == WL_CONNECTED) return true;

  Serial.print("\n[WiFi] Verbinde mit: ");
  Serial.println(WIFI_SSID);

  WiFi.mode(WIFI_STA);
  WiFi.disconnect(true, true);
  delay(200);

  WiFi.begin(WIFI_SSID, WIFI_PASS);

  unsigned long start = millis();
  while (WiFi.status() != WL_CONNECTED && (millis() - start) < WIFI_CONNECT_TIMEOUT_MS) {
    Serial.print(".");
    delay(250);
  }
  Serial.println();

  if (WiFi.status() == WL_CONNECTED) {
    Serial.println("[WiFi] Verbunden ✅");
    Serial.print("IP: "); Serial.println(WiFi.localIP());
    Serial.print("Gateway: "); Serial.println(WiFi.gatewayIP());
    Serial.print("Subnet: "); Serial.println(WiFi.subnetMask());

    logHeader("WiFi verbunden");
    logLine("SSID: " + String(WIFI_SSID));
    logLine("IP: " + ipToString(WiFi.localIP()));
    logLine("Gateway: " + ipToString(WiFi.gatewayIP()));
    logLine("Subnet: " + ipToString(WiFi.subnetMask()));
    return true;
  }

  Serial.println("[WiFi] Verbindung fehlgeschlagen ❌");
  logLine("WiFi Verbindung fehlgeschlagen.");
  return false;
}

// ========== TCP Port Check ==========
bool isPortOpen(IPAddress ip, uint16_t port, uint16_t timeoutMs) {
  WiFiClient client;
  client.setTimeout(timeoutMs);
  bool ok = client.connect(ip, port, timeoutMs);
  client.stop();
  return ok;
}

bool hostSeemsAlive(IPAddress ip) {
  for (int i = 0; i < DISCOVERY_PORTS_COUNT; i++) {
    if (isPortOpen(ip, DISCOVERY_PORTS[i], CONNECT_TIMEOUT_MS)) return true;
  }
  return false;
}

// ========== HostMap (mDNS Namen) ==========
void hostMapClear() { hostMapCount = 0; }

void hostMapPut(IPAddress ip, const String& hostname) {
  for (int i = 0; i < hostMapCount; i++) {
    if (hostMap[i].ip == ip) {
      hostMap[i].hostname = hostname;
      return;
    }
  }
  if (hostMapCount < 30) {
    hostMap[hostMapCount].ip = ip;
    hostMap[hostMapCount].hostname = hostname;
    hostMapCount++;
  }
}

String hostMapGet(IPAddress ip) {
  for (int i = 0; i < hostMapCount; i++) {
    if (hostMap[i].ip == ip) return hostMap[i].hostname;
  }
  return "";
}

// ========== mDNS (FIX: ohne MDNS.IP) ==========
void mdnsBuildMap() {
  hostMapClear();

  if (WiFi.status() != WL_CONNECTED) return;

  const char* myHost = "esp32-toolkit";
  if (!MDNS.begin(myHost)) {
    Serial.println("[mDNS] Start fehlgeschlagen (ok, kann trotzdem weitergehen).");
    logLine("mDNS Start fehlgeschlagen.");
    return;
  }

  Serial.println("[mDNS] Suche nach Gerätenamen (Services) ...");
  logHeader("mDNS Query");

  for (int s = 0; s < MDNS_SERVICE_COUNT; s++) {
    int n = MDNS.queryService(MDNS_SERVICES[s].service, MDNS_SERVICES[s].proto);
    if (n <= 0) continue;

    for (int i = 0; i < n; i++) {
      String h = MDNS.hostname(i);
      if (h.length() == 0) continue;

      IPAddress ip;
      String fqdn = h + ".local";

      if (WiFi.hostByName(fqdn.c_str(), ip)) {
        hostMapPut(ip, h);
        logLine("mDNS: " + fqdn + " -> " + ipToString(ip));
      }
    }
  }

  Serial.print("[mDNS] Namen gefunden: ");
  Serial.println(hostMapCount);
  logLine("mDNS Namen gefunden: " + String(hostMapCount));
}

// ========== Serial Helpers (für Menüpunkt 5) ==========
String readLineFromSerial(unsigned long timeoutMs) {
  String s = "";
  unsigned long start = millis();
  while (millis() - start < timeoutMs) {
    while (Serial.available() > 0) {
      char c = Serial.read();
      if (c == '\r') continue;
      if (c == '\n') return s;
      s += c;
    }
    delay(5);
  }
  return s;
}

bool parseIP(const String& str, IPAddress& out) {
  int a, b, c, d;
  if (sscanf(str.c_str(), "%d.%d.%d.%d", &a, &b, &c, &d) != 4) return false;
  if (a < 0 || a > 255 || b < 0 || b > 255 || c < 0 || c > 255 || d < 0 || d > 255) return false;
  out = IPAddress(a, b, c, d);
  return true;
}

// ========== Features ==========
void wifiScan() {
  Serial.println("\n[1] WLAN Scan startet...");
  logHeader("WLAN Scan");

  WiFi.mode(WIFI_STA);
  WiFi.disconnect(false, false);
  delay(150);

  int n = WiFi.scanNetworks(false, true);
  if (n <= 0) {
    Serial.println("Keine Netze gefunden.");
    logLine("Keine Netze gefunden.");
    return;
  }

  Serial.print("Gefundene Netze: ");
  Serial.println(n);
  Serial.println("---------------------------------------------");

  for (int i = 0; i < n; i++) {
    String ssid = WiFi.SSID(i);
    int32_t rssi = WiFi.RSSI(i);
    int32_t ch = WiFi.channel(i);
    wifi_auth_mode_t enc = WiFi.encryptionType(i);

    String line = String(i + 1) + ") " + ssid +
                  " | RSSI: " + String(rssi) +
                  " dBm | CH: " + String(ch) +
                  " | ENC: " + encTypeName(enc);

    Serial.println(line);
    logLine(line);
  }

  Serial.println("---------------------------------------------");
}

void portScanSingle(IPAddress target, const String& label) {
  String title = "Portscan: " + label + " (" + ipToString(target) + ")";
  Serial.println("\n[" + title + "]");
  logHeader(title);

  int openCount = 0;

  for (int i = 0; i < SCAN_PORTS_COUNT; i++) {
    uint16_t port = SCAN_PORTS[i];
    if (isPortOpen(target, port, CONNECT_TIMEOUT_MS)) {
      openCount++;
      String line = "OPEN: " + String(port);
      Serial.println("✅ " + line);
      logLine(line);
    }
    delay(2);
  }

  if (openCount == 0) {
    Serial.println("Keine offenen Ports aus der Liste gefunden.");
    logLine("Keine offenen Ports (aus Liste).");
  } else {
    Serial.print("Offene Ports (aus Liste): ");
    Serial.println(openCount);
    logLine("Offene Ports Count: " + String(openCount));
  }
}

void scanGatewayRouter() {
  Serial.println("\n[4] Router (Gateway) gezielt scannen...");

  if (!ensureWiFiConnected()) return;

  mdnsBuildMap();

  IPAddress gw = WiFi.gatewayIP();
  String name = hostMapGet(gw);

  Serial.print("Gateway: ");
  Serial.println(gw);

  if (name.length() > 0) portScanSingle(gw, "Gateway/Router: " + name);
  else portScanSingle(gw, "Gateway/Router");
}

void lanDiscovery() {
  Serial.println("\n[2] LAN Discovery startet...");

  if (!ensureWiFiConnected()) return;

  mdnsBuildMap();

  IPAddress ip = WiFi.localIP();
  IPAddress mask = WiFi.subnetMask();
  IPAddress base = networkBase(ip, mask);

  Serial.print("Netz-Basis: ");
  Serial.println(base);

  Serial.println("Suche aktive Hosts (TCP-Check) ...");

  logHeader("LAN Discovery");
  logLine("Base: " + ipToString(base));
  logLine("Self: " + ipToString(ip));

  int found = 0;
  unsigned long start = millis();

  for (int host = 1; host <= 254; host++) {
    IPAddress target(base[0], base[1], base[2], host);
    if (target == ip) continue;

    if (hostSeemsAlive(target)) {
      found++;
      String nm = hostMapGet(target);

      String line = (nm.length() > 0)
        ? ("HOST: " + ipToString(target) + " | " + nm)
        : ("HOST: " + ipToString(target));

      Serial.println("✅ " + line);
      logLine(line);
    }
    delay(5);
  }

  unsigned long dur = millis() - start;

  Serial.println("\n---- Ergebnis ----");
  Serial.print("Gefunden: ");
  Serial.println(found);
  Serial.print("Dauer: ");
  Serial.print(dur);
  Serial.println(" ms");
  Serial.println("------------------");

  logLine("Found: " + String(found));
  logLine("Duration(ms): " + String(dur));
}

void comboScan() {
  Serial.println("\n[3] Combo Scan startet...");
  logHeader("COMBO Scan");

  wifiScan();
  if (!ensureWiFiConnected()) return;

  mdnsBuildMap();

  // 1) Gateway zuerst
  scanGatewayRouter();

  // 2) Discovery + Portscan (max 8 Hosts)
  IPAddress ip = WiFi.localIP();
  IPAddress mask = WiFi.subnetMask();
  IPAddress base = networkBase(ip, mask);

  Serial.println("\n[Combo] Discovery (aktive Hosts) ...");
  logLine("Combo Discovery startet.");

  IPAddress hosts[8];
  int hostCount = 0;

  for (int host = 1; host <= 254; host++) {
    IPAddress target(base[0], base[1], base[2], host);
    if (target == ip) continue;

    if (hostSeemsAlive(target)) {
      String nm = hostMapGet(target);

      Serial.print("✅ Host: ");
      Serial.print(target);
      if (nm.length() > 0) {
        Serial.print(" | ");
        Serial.print(nm);
      }
      Serial.println();

      if (hostCount < 8) {
        hosts[hostCount] = target;
        hostCount++;
      }
    }
    delay(5);
  }

  if (hostCount == 0) {
    Serial.println("[Combo] Keine Hosts für Portscan gefunden.");
    logLine("Combo: keine Hosts für Portscan.");
    return;
  }

  Serial.println("\n[Combo] Portscan der ersten gefundenen Hosts (max 8):");
  logLine("Combo Portscan startet.");

  for (int i = 0; i < hostCount; i++) {
    String nm = hostMapGet(hosts[i]);
    String label = (nm.length() > 0) ? ("Host: " + nm) : "Host";
    portScanSingle(hosts[i], label);
  }

  Serial.println("\n[Combo] Fertig ✅");
  logLine("Combo fertig.");
}

// ======= [5] Target-IP Portscan (manuell) =======
void scanTargetIPInteractive() {
  Serial.println("\n[5] Target-IP Portscan (manuell)");
  if (!ensureWiFiConnected()) return;

  Serial.println("IP eingeben (z.B. 192.168.2.10) und ENTER drücken:");
  Serial.print("IP: ");

  String line = readLineFromSerial(15000);
  line.trim();

  if (line.length() == 0) {
    Serial.println("\n[5] Abbruch: Keine Eingabe.");
    logLine("[5] Abbruch: keine IP eingegeben.");
    return;
  }

  IPAddress target;
  if (!parseIP(line, target)) {
    Serial.println("\n[5] Ungültige IP.");
    logLine("[5] Ungültige IP: " + line);
    return;
  }

  mdnsBuildMap();
  String nm = hostMapGet(target);
  String label = (nm.length() > 0) ? ("Target: " + nm) : "Target";

  portScanSingle(target, label);
}

// ========== Menü ==========
void printMenu() {
  lastMenuPrint = millis();
  Serial.println("\n==============================");
  Serial.println("ESP32 TOOLKIT - MENÜ");
  Serial.println("==============================");
  Serial.println("[1] WLAN Scan (Netze anzeigen)");
  Serial.println("[2] LAN Discovery (Geraete finden + mDNS Namen)");
  Serial.println("[3] Combo (WLAN + Router + LAN + Ports)");
  Serial.println("[4] Router (Gateway) Portscan (gezielt)");
  Serial.println("[5] Target IP Portscan (manuell)");
  Serial.println("[6] WLAN verbinden / Status");
  Serial.println("[7] Log anzeigen (SPIFFS)");
  Serial.println("[8] Log löschen");
  Serial.println("[9] Menü neu anzeigen");
  Serial.println("[10] Hilfe");
  Serial.println("==============================");
  Serial.print("Auswahl: ");
}

void handleChoice(char c) {
  Serial.println(c);

  switch (c) {
    case '1': wifiScan(); break;
    case '2': lanDiscovery(); break;
    case '3': comboScan(); break;
    case '4': scanGatewayRouter(); break;
    case '5': scanTargetIPInteractive(); break;

    case 'c':
      Serial.println("\n[WiFi] Status/Connect:");
      ensureWiFiConnected();
      break;

    case 'l': showLog(); break;
    case 'x': clearLog(); break;

    case 'm': break;

    case 'h':
      Serial.println("\nHilfe:");
      Serial.println("- Oben SSID/PASS eintragen.");
      Serial.println("- Serial Monitor: 115200 Baud.");
      Serial.println("- [4] scannt Gateway (Speedport).");
      Serial.println("- [5] scannt eine manuell eingegebene IP.");
      Serial.println("- Logging: /scan_log.txt (l=anzeigen, x=löschen).");
      Serial.println("- mDNS Namen nur wenn Geräte mDNS anbieten.");
      break;

    default:
      Serial.println("Unbekannte Auswahl. Tippe 1,2,3,4,5,c,l,x,m,h.");
      break;
  }
}

// ========== Arduino ==========
void setup() {
  Serial.begin(115200);
  delay(500);

  Serial.println("\n\n[ESP32 TOOLKIT] gestartet.");
  Serial.println("Hinweis: Nur im eigenen Netzwerk nutzen.");

  initFS();
  logHeader("BOOT");
  logLine("ESP32 Toolkit gestartet.");

  printMenu();
}

void loop() {
  if (Serial.available() > 0) {
    char c = Serial.read();
    if (c == '\n' || c == '\r') return;

    handleChoice(c);
    printMenu();
  }

  if (millis() - lastMenuPrint > 30000) {
    printMenu();
  }

  delay(10);
}
