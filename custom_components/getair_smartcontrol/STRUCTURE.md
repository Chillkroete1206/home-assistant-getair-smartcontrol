# Integration Dateistruktur

## 📁 Vollständige Dateiübersicht

```
custom_components/getair_smartcontrol/
├── __init__.py                  # Integration-Initialisierung & Setup
├── api_cc1.py                   # getAir API (Python SDK)
├── api_client.py                # Wrapper um api_cc1 für HA
├── config_flow.py               # Konfigurationsfluss (UI)
├── const.py                     # Konstanten (Domain, Hersteller, etc.)
├── coordinator.py               # DataUpdateCoordinator (Polling)
├── fan.py                       # FanEntity für Zonen (Steuerung)
├── sensor.py                    # SensorEntity für Messwerte
├── manifest.json                # Integration-Metadaten
├── strings.json                 # UI-Texte (mehrsprachig)
├── py.typed                     # Marker für Type-Hints
├── README.md                    # Hauptdokumentation
├── INSTALLATION.md              # Detaillierte Installation
├── SETUP_GUIDE.md               # Schnelleinstieg
└── STRUCTURE.md                 # Diese Datei
```

## 📄 Datei-Beschreibungen

### `__init__.py` (87 Zeilen)
**Zweck**: Integration-Einstiegspunkt für Home Assistant

**Inhalt**:
- `async_setup_entry()` - Hauptsetup-Funktion
- Coordinator-Initialisierung
- Entitäten-Setup für Fan und Sensoren
- Unload-Funktion

### `api_cc1.py` (913 Zeilen)
**Zweck**: getAir SmartControl Python API SDK

**Inhalt**:
- `ResponseCode` Enum - HTTP-Status-Codes
- `API` Klasse - Authentifizierung & Token-Management
- `Device` Klasse - Gerätekontrolle (System + 3 Zonen)
- Token-Refresh Logik
- Rate-Limit Prevention

**Wichtig**: Dies ist die ursprüngliche Datei aus dem Python SDK mit Verbesserungen!

### `api_client.py` (62 Zeilen)
**Zweck**: Adapter zwischen HA und api_cc1.py

**Inhalt**:
- `GetAirAPIClient` Klasse
- Import der api_cc1 API
- Credentials-Verwaltung
- Device-Abruf-Wrapper

### `config_flow.py` (156 Zeilen)
**Zweck**: Benutzerfreundlicher Setup-Dialog

**Funktionalität**:
- Schritt 1: Benutzer-Eingaben (Credentials)
- Validierung der Eingaben
- Duplikat-Erkennung
- Options-Flow für Einstellungen

### `const.py` (11 Zeilen)
**Zweck**: Zentrale Konstanten

**Inhalt**:
```python
DOMAIN = "getair_smartcontrol"
MANUFACTURER = "getAir"
CONF_AUTH_URL = "auth_url"
CONF_API_URL = "api_url"
CONF_CLIENT_ID = "client_id"
CONF_DEVICE_ID = "device_id"
MODES = ["ventilate", "ventilate_hr", ...]
```

### `coordinator.py` (168 Zeilen)
**Zweck**: Zentrales Polling und Daten-Verwaltung

**Klasse**: `GetAirCoordinator(DataUpdateCoordinator)`

**Funktionen**:
- `_async_update_data()` - Polling-Routine
- `async_set_zone_speed()` - Speed-Steuerung
- `async_set_zone_mode()` - Modus-Steuerung
- Async-Wrapper für Sync-API

**Polling-Intervall**: Konfigurierbar (Default: 60s)

### `fan.py` (156 Zeilen)
**Zweck**: Fan-Entitäten für Zonen

**Klasse**: `GetAirZoneFan(CoordinatorEntity, FanEntity)`

**Entitäten** (3×):
- `fan.getair_smartcontrol_zone_1`
- `fan.getair_smartcontrol_zone_2`
- `fan.getair_smartcontrol_zone_3`

**Services**:
- `turn_on()` - Lüfter an (auf 30%)
- `turn_off()` - Lüfter aus (auf Minimum)
- `set_percentage()` - Geschwindigkeit setzen (0-100%)

### `sensor.py` (183 Zeilen)
**Zweck**: Sensoren für Messwerte

**Sensoren pro Zone** (3×):
- Temperatur
- Luftfeuchtigkeit
- Außentemperatur
- Außenluftfeuchte

**System-Sensoren** (4×):
- Luftqualität (ppm)
- Luftdruck (hPa)
- Relative Feuchte (%)
- Innentemperatur (°C)

**Gesamt**: ~16 Entitäten

### `manifest.json` (11 Zeilen)
**Zweck**: Integration-Metadaten

```json
{
  "domain": "getair_smartcontrol",
  "name": "getAir SmartControl",
  "version": "1.0.0",
  "config_flow": true,
  "requirements": [],
  "iot_class": "cloud_polling"
}
```

### `strings.json` (48 Zeilen)
**Zweck**: UI-Texte und Mehrsprachigkeit

**Inhalt**:
- Config-Flow Beschreibungen
- Fehler-Meldungen
- Optionen-Texte
- Feldbezeichnungen

### `py.typed` (0 Zeilen)
**Zweck**: Marker für Type-Hints Support

Ermöglicht Mypy und anderen Type-Checkern, Typ-Informationen zu nutzen.

### Dokumentation

| Datei | Zweck | Zielgruppe |
|-------|-------|-----------|
| `README.md` | Vollständige Features & Beispiele | Benutzer |
| `INSTALLATION.md` | Schritt-für-Schritt Installation | Benutzer |
| `SETUP_GUIDE.md` | Schnelleinstieg | Ungeduld Menschen 😄 |
| `STRUCTURE.md` | Technische Übersicht | Entwickler |

---

## 🔄 Datenfluss

```
Home Assistant
    ↓
config_flow.py (User Input)
    ↓
__init__.py (Setup)
    ↓
api_client.py
    ↓
api_cc1.py (getAir API)
    ↓
getAir Server
    ↓
Gerät Daten
    ↓
coordinator.py (Caching & Polling)
    ↓
fan.py + sensor.py (Entitäten)
    ↓
Home Assistant UI
```

## 🎯 Wichtige Klassen

```
HomeAssistant Config Entry
    ↓
GetAirAPIClient (api_client.py)
    ↓ Instantiiert
API (api_cc1.py)
    ↓ Authentifizierung
Token + Device
    ↓
GetAirCoordinator (coordinator.py)
    ↓ Polling alle 60s
{system, zones}
    ↓
GetAirZoneFan (fan.py) + GetAirSensor (sensor.py)
    ↓
Home Assistant Entities
```

## 📊 Entitäten-Übersicht

### Fan-Entitäten (3)
```
entity_id                              | Type | Control
fan.getair_smartcontrol_zone_1        | Fan  | Speed, On/Off
fan.getair_smartcontrol_zone_2        | Fan  | Speed, On/Off
fan.getair_smartcontrol_zone_3        | Fan  | Speed, On/Off
```

### Sensor-Entitäten (16)
```
System (4):
sensor.getair_smartcontrol_temperature
sensor.getair_smartcontrol_humidity
sensor.getair_smartcontrol_air_pressure
sensor.getair_smartcontrol_air_quality

Zone 1 (4):
sensor.getair_smartcontrol_zone_1_temperature
sensor.getair_smartcontrol_zone_1_humidity
sensor.getair_smartcontrol_zone_1_outdoor_temperature
sensor.getair_smartcontrol_zone_1_outdoor_humidity

Zone 2 (4): ... similar ...
Zone 3 (4): ... similar ...
```

**Gesamt: 19 Entitäten**

## 🔐 Credentials-Flow

```
User Input (config_flow.py)
    ↓
{
  "auth_url": "https://auth.getair.eu/oauth/token",
  "api_url": "https://be01.ga-cc.de/api/v1/",
  "client_id": "xxx",
  "username": "xxx",
  "password": "xxx",
  "device_id": "80C9553981A0"
}
    ↓
Home Assistant Config Entry
    ↓
GetAirAPIClient
    ↓
api_cc1.py API.connect()
    ↓
OAuth Token (expires in 1 hour)
    ↓
Automatisches Refresh vor Ablauf
```

## 🚨 Fehlerbehandlung

```
API-Call
    ↓
401 Unauthorized?
    ↓ Ja
try reconnect (1x)
    ↓
Success? → Continue
Fail? → Log Error & Return None
    ↓
No → Continue normally
```

---

**Version**: 1.0.0  
**Stand**: 25.01.2026
