# Installation der getAir SmartControl Home Assistant Integration

## Übersicht

Diese Anleitung erklärt, wie du die getAir SmartControl Integration in deinem Home Assistant installierst.

## Voraussetzungen

- Home Assistant 2023.12 oder neuer
- Zugriff auf die Home Assistant Konfigurationsdateien
- getAir SmartControl Gerät mit API-Zugang
- Anmeldedaten für die getAir API:
  - Email/Benutzername
  - Passwort
  - Client-ID
  - Auth-URL: `https://auth.getair.eu/oauth/token`
  - API-URL: `https://be01.ga-cc.de/api/v1/`
- MAC-Adresse des Geräts (z.B. `80C9553981A0`)

## Schritt 1: Integration-Dateien kopieren

1. **Lade die Integration herunter** oder klone das Repository
2. **Kopiere den Ordner** `custom_components/getair_smartcontrol/` in deinen `config/custom_components/` Ordner in Home Assistant

Deine Struktur sollte dann aussehen wie:

```
home-assistant/config/
├── configuration.yaml
├── automations.yaml
├── scenes.yaml
├── scripts.yaml
├── custom_components/
│   └── getair_smartcontrol/
│       ├── __init__.py
│       ├── api_cc1.py              # ← Wichtig!
│       ├── api_client.py
│       ├── config_flow.py
│       ├── const.py
│       ├── coordinator.py
│       ├── fan.py
│       ├── manifest.json
│       ├── sensor.py
│       ├── strings.json
│       ├── py.typed
│       ├── README.md
│       └── INSTALLATION.md
```

## Schritt 2: Überprüfe die Integration

Verifiziere, dass alle Dateien vorhanden sind, besonders:
- ✅ `api_cc1.py` (die API-Klasse)
- ✅ `manifest.json` (Integration-Metadaten)
- ✅ `__init__.py` (Initialisierung)

## Schritt 3: Home Assistant neu starten

```bash
# Wenn du Docker verwendest:
docker restart homeassistant

# Wenn du direkt installiert hast:
systemctl restart home-assistant
# oder einfach via Home Assistant UI neustarten
```

## Schritt 4: Integration in Home Assistant hinzufügen

### Methode A: Via Web-UI (Empfohlen)

1. Öffne Home Assistant im Browser: `http://192.168.x.x:8123`
2. Gehe zu **Einstellungen** (Zahnrad oben links)
3. Navigiere zu **Geräte und Dienste**
4. Klicke auf den Button **"Neue Integration erstellen"** (rechts unten)
5. Suche nach **"getAir SmartControl"** (nicht "getAir" allein!)
6. Klicke auf die Integration zum Hinzufügen
7. Fülle das Formular aus mit deinen getAir-Anmeldedaten:

```
Authentifizierungs-URL:  https://auth.getair.eu/oauth/token
API-URL:                 https://be01.ga-cc.de/api/v1/
Client-ID:               <deine-client-id>
Benutzername:            <deine-email>
Passwort:                <dein-passwort>
Geräte-ID:               80C9553981A0  (oder deine MAC-Adresse)
```

8. Klicke auf **"Abschicken"**

### Methode B: Via YAML (Manuell)

Falls die UI nicht funktioniert, füge dies in `configuration.yaml` hinzu:

```yaml
getair_smartcontrol:
  auth_url: "https://auth.getair.eu/oauth/token"
  api_url: "https://be01.ga-cc.de/api/v1/"
  client_id: "YOUR_CLIENT_ID"
  username: "YOUR_EMAIL"
  password: "YOUR_PASSWORD"
  device_id: "80C9553981A0"
```

Starte Home Assistant neu.

## Schritt 5: Konfiguration (Optional)

Nach der Installation kannst du Optionen einstellen:

1. Gehe zu **Einstellungen** → **Geräte und Dienste** → **Integrationen**
2. Suche die **getAir SmartControl** Integration
3. Klicke auf die **3 Punkte** (oben rechts)
4. Wähle **"Optionen"**
5. Stelle folgende Parameter ein:

| Parameter | Standard | Beschreibung |
|-----------|----------|-------------|
| Polling-Intervall | 60 | Sekunden zwischen API-Abfragen (10-3600) |
| Zone 1 aktivieren | ✓ | Zone 1 als Entität erstellen |
| Zone 2 aktivieren | ✓ | Zone 2 als Entität erstellen |
| Zone 3 aktivieren | ✓ | Zone 3 als Entität erstellen |

## Schritt 6: Überprüfe die Entitäten

Nach erfolgreichem Setup sollten folgende Entitäten vorhanden sein:

### Fan-Entitäten (Zonen)
```
fan.getair_smartcontrol_zone_1
fan.getair_smartcontrol_zone_2
fan.getair_smartcontrol_zone_3
```

### Sensor-Entitäten
```
sensor.getair_smartcontrol_temperature
sensor.getair_smartcontrol_humidity
sensor.getair_smartcontrol_air_pressure
sensor.getair_smartcontrol_air_quality

sensor.getair_smartcontrol_zone_1_temperature
sensor.getair_smartcontrol_zone_1_humidity
sensor.getair_smartcontrol_zone_1_outdoor_temperature
sensor.getair_smartcontrol_zone_1_outdoor_humidity
# ... etc. für Zone 2 und 3
```

## Fehlerbehebung

### Fehler: "Integration nicht gefunden"

**Lösung:**
- Stelle sicher, dass die Dateien in `config/custom_components/getair_smartcontrol/` sind
- Home Assistant MUSS neu gestartet sein nach dem Kopieren
- Prüfe die Logs: **Einstellungen** → **Protokolle** (suche nach `getair`)

### Fehler: "Cannot connect to API"

**Gründe & Lösungen:**
- **Ungültige Anmeldedaten**: Prüfe Email, Passwort, Client-ID
- **Falsche URLs**: Stelle sicher, dass du die korrekten URLs einsetzt (siehe Schritt 4)
- **Geräte-ID falsch**: MAC-Adresse muss 12 Zeichen sein (z.B. `80C9553981A0`, nicht `80:C9:55:39:81:A0`)
- **Netzwerkfehler**: Prüfe die Internetverbindung deines HA-Systems

Logs prüfen:
```
Einstellungen → Protokolle → Filter: "getair" → Aktualisieren
```

### Fehler: "Device not found"

**Lösung:**
- Prüfe die MAC-Adresse des Geräts
- Alle 12 Zeichen müssen vorhanden sein
- Keine Doppelpunkte oder Bindestriche

### Entitäten fehlen

**Lösung:**
- Prüfe die Optionen (Zone aktiviert?)
- Warte 60 Sekunden (Standard Polling-Intervall)
- Home Assistant neu laden: **Einstellungen** → **Protokolle** → Button **"Server-Kontrollen"** → **"Schnellstart"**

## Debugging aktivieren

Um Debugging-Informationen zu sehen:

1. Öffne `configuration.yaml`
2. Füge diese Zeilen hinzu:

```yaml
logger:
  default: info
  logs:
    custom_components.getair_smartcontrol: debug
    custom_components.getair_smartcontrol.api_client: debug
    custom_components.getair_smartcontrol.coordinator: debug
```

3. Speichere und starte Home Assistant neu
4. Gehe zu **Einstellungen** → **Protokolle** und suche nach Errors

## Nächste Schritte

Nach erfolgreicher Installation:

1. **Dashboard erstellen**: Erstelle eine neue Dashboard mit den Fan- und Sensor-Entitäten
2. **Automationen schreiben**: Erstelle Automationen zur automatischen Lüftersteuerung
3. **Szenen erstellen**: Definiere Szenen für verschiedene Betriebsmodi (z.B. "Gut schlafen", "Produktiv arbeiten")

## Support

Bei Problemen:

1. Prüfe die [README.md](README.md) für weitere Informationen
2. Schau in die Logs (wie oben beschrieben)
3. Erstelle ein Issue im GitHub-Repository mit:
   - Home Assistant Version
   - Fehler-Logs (bereinigt von sensiblen Daten)
   - Beschreibung des Problems

## Technische Informationen

### Geräte-ID Struktur

Die getAir SmartControl nutzt folgende Geräte-IDs:

```
System:  AABBCCDDEEFF         (z.B. 80C9553981A0)
Zone 1:  1.AABBCCDDEEFF       (z.B. 1.80C9553981A0)
Zone 2:  2.AABBCCDDEEFF       (z.B. 2.80C9553981A0)
Zone 3:  3.AABBCCDDEEFF       (z.B. 3.80C9553981A0)
```

Die Integration kümmert sich um diese Unterscheidung automatisch.

### Rate-Limiting

Die getAir API hat folgende Limitierungen:
- 5 Authentifizierungen pro Minute
- Token-Gültigkeit: 1 Stunde
- Automatisches Refresh 1 Minute vor Ablauf

Die Integration handhabt dies automatisch.

---

**Version**: 1.0.0  
**Letztes Update**: 25.01.2026
