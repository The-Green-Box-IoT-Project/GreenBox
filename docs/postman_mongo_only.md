# Postman – test API Catalog (solo Mongo)

Questa guida testa **catalog** + **mongo-adapter** + **mongo** (senza Influx).

## 1) Avvio stack (solo Mongo)

Da root progetto:

- `docker compose up -d mongo mongo-adapter catalog`

Nota: in [docker-compose.yml](docker-compose.yml) i servizi Influx sono sotto `profiles: ["influx"]`, quindi **non partono** di default.

## 2) Variabili Postman consigliate

Crea un Environment Postman (es. `GreenBox Local`) con:

- `CATALOG_BASE_URL` = `http://localhost:8080`
- `TOKEN` = (vuoto, lo setti dopo login)

Per tutte le richieste **eccetto** login/register aggiungi header:

- `token: {{TOKEN}}`

## 3) Flusso minimo di test (ordine consigliato)

### A) Register
  ```json
  {"username":"testuser","password":"testpass"}
  ```
  Body JSON (email is required):
  ```json
  {"username":"testuser","password":"testpass","email":"testuser@example.com"}
  ```

### B) Login
- `POST {{CATALOG_BASE_URL}}/login`
- Body JSON:
  ```json
  {"username":"testuser","password":"testpass"}
  ```
- Atteso: `200` con
  ```json
  {"token":"..."}
  ```
- Salva `token` in env var `TOKEN`.

### C) User info
- `GET {{CATALOG_BASE_URL}}/user/info`
- Header `token`
- Atteso: `200` con `{ "username": "testuser" }`

### D) Greenhouses
- `POST {{CATALOG_BASE_URL}}/greenhouses`
- Header `token`
- Body JSON:
  ```json
  {"name":"Serra Test"}
  ```
- Atteso: `200`

- `GET {{CATALOG_BASE_URL}}/greenhouses`
- Header `token`
- Atteso: `200` con lista di oggetti `{id, name}`.

### E) Zones
- `GET {{CATALOG_BASE_URL}}/zones?greenhouse_id=<ID_GREENHOUSE>`
- Header `token`
- Atteso: `200` con lista `{id, name}`.

- `PUT {{CATALOG_BASE_URL}}/zones?greenhouse_id=<ID_GREENHOUSE>&zone_id=Z_123&name=Zona 123`
- Header `token`
- Atteso: `200`

- `PUT {{CATALOG_BASE_URL}}/zones/validate?zone_id=Z_123`
- Header `token`
- Atteso: `200` con `true`.

### F) Control strategy
- `PUT {{CATALOG_BASE_URL}}/zones/strategy?zone_id=Z_123`
- Header `token`
- Body JSON (esempio):
  ```json
  {
    "temperature": {"min": 18, "max": 26},
    "soilHumidity": {"min": 0.25, "max": 0.45},
    "airHumidity": {"min": 0.40, "max": 0.70}
  }
  ```

- `GET {{CATALOG_BASE_URL}}/zones/strategy?zone_id=Z_123`

## 4) Note importanti

- Letture/mutazioni su risorse non owned ora ritornano `403`.
- Risorsa inesistente tipicamente ritorna `404`.
- Duplicati (nome serra o nome zona già esistenti) ritornano `409`.

