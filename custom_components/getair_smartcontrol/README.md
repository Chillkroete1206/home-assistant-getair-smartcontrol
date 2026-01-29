# getAir SmartControl - Home Assistant Integration

Eine vollständige Home Assistant Custom Integration für die getAir SmartControl Lüftungsanlage.

## Features

- ✅ **Multi-Zone Steuerung**: Kontrolle aller 3 Lüftungszonen unabhängig voneinander
- ✅ **Fan-Entities**: Jede Zone als `fan`-Entity mit Geschwindigkeitsregler
- ✅ **Sensoren**: Temperatur, Luftfeuchtigkeit, Luftqualität und Außenbedingungen
- ✅ **Automatisches Polling**: Konfigurierbare Abfrage-Intervalle (10-3600 Sekunden)
- ✅ **Rate-Limit Protection**: Intelligentes Token-Management, keine Rekursionsschleifen
- ✅ **HA Standard**: Nutzt DataUpdateCoordinator, vollständig async

## Installation

### 1. Kopieren der Integration

Die Integration muss in `config/custom_components/getair_smartcontrol/` platziert werden:

```bash
config/
└── custom_components/
    └── getair_smartcontrol/
        ├── __init__.py
        ├── api_client.py
        ├── config_flow.py
        ├── const.py
        ├── coordinator.py
        ├── fan.py
        ├── sensor.py
        ├── manifest.json
        ├── strings.json
        └── py.typed
```

### 2. Kopieren der API-Datei

Die `api_cc1.py` muss ebenfalls verfügbar sein. Am besten in der Integration oder über PYTHONPATH:

```bash
custom_components/getair_smartcontrol/
├── api_cc1.py  # <-- Kopieren Sie diese Datei hier hin
```

### 3. Home Assistant neu starten

Nach dem Kopieren Home Assistant neustarten, damit die Integration geladen wird.

### 4. Integration hinzufügen

1. Gehen Sie zu **Einstellungen** → **Geräte und Dienste** → **Integrationen**
2. Klicken Sie auf **"Neue Integration erstellen"** (rechts unten)
3. Suchen Sie nach **"getAir SmartControl"**
4. Geben Sie Ihre getAir-Anmeldedaten ein:
   - **Authentifizierungs-URL**: `https://auth.getair.eu/oauth/token`
   - **API-URL**: `https://be01.ga-cc.de/api/v1/`
   - **Client-ID**: Ihre getAir Client-ID
   - **Benutzername**: Ihre getAir Email
   - **Passwort**: Ihr getAir Passwort
   - **Geräte-ID**: MAC-Adresse (z.B. `80C9553981A0`)

## Konfiguration

Nach der Installation können Sie folgende Optionen einstellen:

- **Abfrage-Intervall** (Polling Interval): 10-3600 Sekunden (Standard: 60)
- **Zone 1 aktivieren**: Ein-/Ausschalten der Zone
- **Zone 2 aktivieren**: Ein-/Ausschalten der Zone
- **Zone 3 aktivieren**: Ein-/Ausschalten der Zone

## Entitäten

### Fan-Entities (für jede Zone)

```
fan.getair_smartcontrol_zone_1  # Zone 1 Lüfter
fan.getair_smartcontrol_zone_2  # Zone 2 Lüfter
fan.getair_smartcontrol_zone_3  # Zone 3 Lüfter
```

**Services**:
- `fan.turn_on`: Lüfter einschalten (auf 30%)
- `fan.turn_off`: Lüfter ausschalten (auf Minimum)
- `fan.set_percentage`: Geschwindigkeit setzen (0-100%)

**Verfügbare Geschwindigkeiten**:
```
15% = 0.5
30% = 1.0
45% = 1.5
60% = 2.0
75% = 2.5
85% = 3.0
95% = 3.5
100% = 4.0
```

### Sensor-Entities

**System (Gesamt)**:
- `sensor.getair_smartcontrol_air_quality` - Luftqualität (ppm)
- `sensor.getair_smartcontrol_air_pressure` - Luftdruck (hPa)
- `sensor.getair_smartcontrol_humidity` - Relative Feuchte (%)
- `sensor.getair_smartcontrol_temperature` - Innentemperatur (°C)

**Pro Zone** (1-3):
- `sensor.getair_smartcontrol_zone_x_temperature` - Temperatur
- `sensor.getair_smartcontrol_zone_x_humidity` - Luftfeuchtigkeit
- `sensor.getair_smartcontrol_zone_x_outdoor_temperature` - Außentemperatur
- `sensor.getair_smartcontrol_zone_x_outdoor_humidity` - Außenluftfeuchte

## Automatisierungsbeispiele

### Beispiel 1: Lüfter basierend auf Temperatur steuern

```yaml
automation:
  - alias: "Lüfter bei Überhitzung aktivieren"
    trigger:
      platform: numeric_state
      entity_id: sensor.getair_smartcontrol_zone_1_temperature
      above: 26
    action:
      service: fan.set_percentage
      target:
        entity_id: fan.getair_smartcontrol_zone_1
      data:
        percentage: 100
```

### Beispiel 2: Zeit-basierte Steuerung

```yaml
automation:
  - alias: "Morgens Lüfter auf 50%"
    trigger:
      platform: time
      at: "07:00:00"
    action:
      service: fan.set_percentage
      target:
        entity_id: 
          - fan.getair_smartcontrol_zone_1
          - fan.getair_smartcontrol_zone_2
          - fan.getair_smartcontrol_zone_3
      data:
        percentage: 60
```

### Beispiel 3: Dashboard Card

```yaml
type: entities
entities:
  - entity: fan.getair_smartcontrol_zone_1
    name: Wohnzimmer
  - entity: fan.getair_smartcontrol_zone_2
    name: Schlafzimmer
  - entity: fan.getair_smartcontrol_zone_3
    name: Küche
  - entity: sensor.getair_smartcontrol_zone_1_temperature
    name: Wohnzimmer Temp.
  - entity: sensor.getair_smartcontrol_zone_1_humidity
    name: Wohnzimmer Feuchte
title: getAir SmartControl
```

## Fehlerbehebung

### "Cannot connect to API"
- Prüfen Sie die Anmeldedaten (Auth-URL, API-URL, Client-ID)
- Stellen Sie sicher, dass die .credentials Datei vorhanden ist
- Prüfen Sie die Netzwerkverbindung

### "Device not found"
- Prüfen Sie die Geräte-ID (MAC-Adresse)
- Die ID sollte 12 Zeichen lang sein (ohne Doppelpunkte)

### "401 Unauthorized" in Logs
- Das ist normal und wird automatisch behoben
- Die Integration versucht automatisch, sich neu zu authentifizieren

### Integration lädt nicht
- Prüfen Sie, dass `api_cc1.py` im Pfad ist
- Überprüfen Sie die Python-Logs auf Fehler
- Versuchen Sie Home Assistant neu zu starten

## Entwicklung

### Debugging aktivieren

In `configuration.yaml`:

```yaml
logger:
  default: info
  logs:
    custom_components.getair_smartcontrol: debug
    custom_components.getair_smartcontrol.api_client: debug
    custom_components.getair_smartcontrol.coordinator: debug
```

### API-Dokumentation

Die Integration nutzt die `api_cc1.py` Datei aus dem getAir SmartControl Python SDK.

## Lizenz

MIT

## Support

Bei Fragen oder Problemen: [GitHub Issues](https://github.com/yourusername/home-assistant-getair-smartcontrol/issues)

## Versionsgeschichte

### v1.0.0 (2026-01-25)
- Initiale Version
- Fan-Entitäten für 3 Zonen
- Sensor-Entitäten für Messwerte
- DataUpdateCoordinator mit Polling
- Config Flow für einfaches Setup
