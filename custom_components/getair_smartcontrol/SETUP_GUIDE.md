# getAir SmartControl Home Assistant Integration - Quick Start

## 🚀 Schnelleinstieg (5 Minuten)

### 1. Dateien kopieren

```bash
# Kopiere den Integration-Ordner
cp -r custom_components/getair_smartcontrol /path/to/homeassistant/config/custom_components/
```

**Wichtig:** Stelle sicher, dass die Datei `api_cc1.py` im Ordner vorhanden ist!

### 2. Home Assistant neu starten

- Web-UI: **Einstellungen** → **System** → **Server-Kontrollen** → **Server neu starten**
- Oder über Terminal: `docker restart homeassistant` (falls Docker)

### 3. Integration hinzufügen

1. **Einstellungen** → **Geräte und Dienste**
2. **Neue Integration** (rechts unten)
3. Suche: **"getAir SmartControl"**
4. Anmeldedaten eingeben:

| Feld | Wert | Beispiel |
|------|------|---------|
| Auth-URL | Fest | `https://auth.getair.eu/oauth/token` |
| API-URL | Fest | `https://be01.ga-cc.de/api/v1/` |
| Client-ID | Von getAir | `abc123xyz` |
| Benutzername | Deine Email | `email@example.com` |
| Passwort | Dein Passwort | `••••••••` |
| Geräte-ID | MAC des Geräts | `80C9553981A0` |

5. **Speichern** → **Fertig**

### 4. Fertig! 🎉

Deine Entitäten sollten jetzt verfügbar sein:
- `fan.getair_smartcontrol_zone_1` → Zum Steuern der Zone
- `sensor.getair_smartcontrol_zone_1_temperature` → Temperaturmessung
- etc.

---

## 📋 Checkliste vor dem Setup

- [ ] Home Assistant 2023.12+ vorhanden
- [ ] Zugriff auf `config/` Ordner
- [ ] getAir SmartControl Anmeldedaten bereit
- [ ] MAC-Adresse des Geräts bekannt
- [ ] Python 3.11+ (Home Assistant Standard)

---

## 🔧 Häufigste Probleme

### "Integration nicht sichtbar"
→ Home Assistant **komplett** neu starten (nicht nur laden)

### "Cannot connect"
→ Anmeldedaten prüfen (besonders Client-ID!)

### "Device not found"
→ MAC-Adresse muss genau 12 Zeichen sein

---

## 📚 Weitere Dokumentation

- **[INSTALLATION.md](INSTALLATION.md)** - Detaillierte Installationsanleitung
- **[README.md](README.md)** - Alle Features und Automationsbeispiele
- **[Fehlersuche](README.md#fehlerbehebung)** - Lösungen für Probleme

---

## 💡 Erste Automatisierung

Nach erfolgreichem Setup kannst du sofort loslegen:

```yaml
automation:
  - alias: "Morgens lüften"
    trigger:
      platform: time
      at: "07:00:00"
    action:
      service: fan.set_percentage
      target:
        entity_id: fan.getair_smartcontrol_zone_1
      data:
        percentage: 60
```

---

**Brauchst du Hilfe?** → Siehe [README.md](README.md#fehlerbehebung)
