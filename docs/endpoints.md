# GreenBox Catalog API (aggiornato)

Tutte le API (tranne signup/login) richiedono il token. Puoi passarlo via header `token: <JWT>` o query `?token=...`.

## Autenticazione
- `POST /signup`  
  Body: `{"username":"alice88","password":"secret"}`  
  Risposta: `{"token":"..."}`  
- `POST /login`  
  Body: `{"username":"alice88","password":"secret"}`  
  Risposta: `{"token":"..."}`  
- `POST /login` con query `token=<token>` (token login)  
  Risposta: `{"token":"...", "valid": true/false, "greenhouses":[...]}`  

## Utente
- `GET /user`  
  Auth: `token`  
  Risposta: `{"username":"alice88","country":"IT","account_level":"standard"}`

## Greenhouses
- `POST /greenhouses`  
  Auth: `token`  
  Body: `{"name":"Serra Nord"}`  
  Risposte: `{"greenhouse_id":"<generated>","name":"Serra Nord"}`; `409 greenhouse_name_taken` se nome già usato dallo stesso utente.
- `GET /retrieve/greenhouses?token=...`  
  Auth: `token` (query o header)  
  Risposta: `{"greenhouses":[...]}` (fonte Mongo).

## Devices
- `GET /retrieve/devices?greenhouse_id=...`  
  Auth: `token`  
  Risposta: `{"devices":[...]}`
- `PUT /associate/device?device_id=...&greenhouse_id=...&device_name=...`  
  Auth: `token`  
  Controlli: device esistente, serra esistente, proprietà utente, device non già associato, nome unico per serra.  
  Risposta: `{"status":"success", ...}` oppure `409 device_already_associated` / `409 device_name_taken`.
- `GET /devices/{device_id}/config`  
  Auth: non richiesto  
  Risposta: `{"device_id":...,"greenhouse_id":...,"broker_ip":...,"broker_port":...,"device_type":...,"role":...}`
- `GET /devices/{device_id}/actuator-info`  
  Auth: `token`  
  Solo per attuatori; controlla ownership serra.  
  Risposta: `{"device_id":...,"name":...,"device_type":...,"role":...,"greenhouse_id":...,"strategy_id":...,"bound_device_id":...}`
- `PUT /actuators/{device_id}/bind?raspberry_id=...`  
  Auth: `token`  
  Controlli: attuatore valido, raspberry/controller valido, stessa serra, proprietà utente.  
  Risposta: `{"msg":"bind_ok",...}`

## Misure
- `GET /measures?device_id=...&metric=temperature&range=1h`  
  Auth: `token`  
  metric consentite: temperature, humidity, light, soil_humidity, pH/ph.  
  range consentiti: 1h, 6h, 1d, 7d, 1m, 3m, 1y.  
  Risposta: `{"device_id":...,"metric":"temperature","range":"1h","points":[{"ts":"...","value":24.1},...]}` (max 60 punti). Fonte Mongo `telemetry`, fallback file `catalog/services/telemetry.json`.

## Strategia/colture
- `POST /greenhouse/crop?greenhouse_id=...&crop=...`  
  Auth: `token`  
  Risposta: `{"msg":"crop_set", ...}`; 404 se serra/crop non trovati.
- `PUT /strategy?greenhouse_id=...&update=<json>`  
  Auth: `token`  
  Body param `update` in JSON string.

## Broker e config
- `GET /broker`  
  Risposta: `{"broker_ip": "...", "broker_port": 1883}`  
- `GET /greenhouses/{id}/thresholds`  
  Auth: non richiesto  
  Risposta: `{"greenhouse_id": "...", "thresholds": {...}}`
- `GET /greenhouses/{id}/effects`  
  Auth: non richiesto  
  Risposta: `{"greenhouse_id": "...", "effects": [...]}` (modelli attuatori).

## Note
- Admin-only: `GET /generate_id`, `POST /register/device`, `POST /register/greenhouse` richiedono header `token` uguale a `ADMIN_TOKEN`.
- Autenticazione: `token` può stare negli header o nella query; se assente/invalid -> 401. Log-in e signup restano aperti.
