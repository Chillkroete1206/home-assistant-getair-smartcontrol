# Test der API-Fixes

## Problem-Diagnose
Der API-Client konnte sich authentifizieren, aber `device.fetch()` schlug mit 401 fehl.

## Root Cause
- AUTO_RECONNECT war auf False gesetzt
- Nach einem Token-Refresh war das neue Token nicht sofort gültig
- Der API-Server brauchte Zeit, das neue Token zu aktivieren

## Implementierte Fixes

### 1. AUTO_RECONNECT Re-Enabled (api_client.py)
```python
self._api.AUTO_RECONNECT = True
```
**Auswirkung**: Die API kann jetzt automatisch versuchen, sich bei 401-Fehlern zu reconnecten

### 2. Längere Wartezeiten nach Token-Refresh (api_cc1.py)
```python
time.sleep(1.0)  # Nach Token-Refresh
```
**Auswirkung**: Der Server hat 1 Sekunde Zeit, das neue Token zu aktivieren

### 3. Token-Validierung (api_cc1.py)
```python
if not self._api_token:
    self._logger.error("No API token available")
    return None
```
**Auswirkung**: Bessere Fehlerbehandlung bei fehlenden Tokens

### 4. Längere Wartezeiten im Coordinator (coordinator.py)
```python
time.sleep(1.5)  # Nach Reconnect
```
**Auswirkung**: Mehr Zeit für Token-Propagation vor erneutem Fetch

## Test-Anweisungen

1. **Home Assistant neustarten** oder Custom Component neu laden
2. **In den Logs prüfen auf**:
   - "Successfully refreshed token" oder "Successfully authenticated"
   - Dann sollte "Got 401" NICHT mehr auftauchen
   - Stattdessen sollten die Geräte-Daten erfolgreich abgerufen werden

3. **Erwartete Log-Sequenz nach Fix**:
   ```
   Successfully authenticated
   Successfully fetched device data
   Created sensor entities
   ```

4. **Keine 401-Fehler mehr** nach initialer Authentifizierung

## Fallback-Optionen
Wenn die Fix immer noch nicht funktioniert:

1. **Erhöhen Sie die Wartezeiten** in `api_cc1.py`:
   ```python
   time.sleep(2.0)  # Noch längerer Delay
   ```

2. **Prüfen Sie die Server-Logs**, ob das Credentials-Objekt korrekt ist

3. **Testen Sie mit dem originalen Script** (`set_zone_speed_Claude.py`), das bekanntermaßen funktioniert
