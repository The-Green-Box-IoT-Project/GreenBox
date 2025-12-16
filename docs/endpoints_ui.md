# GreenBox API Documentation

Questa documentazione descrive gli endpoint esposti dal **Catalog Service** per l'interfaccia utente (UI).

**Base URL**: `http://<catalog-ip>:<catalog-port>` (Default: `http://localhost:8080`)

**Autenticazione**:
Tutte le chiamate (eccetto Login e Registrazione) richiedono un header `token` con il token JWT ricevuto al login.

---

## 1. Autenticazione

### Login
*   **URL**: `/login`
*   **Method**: `POST`
*   **Body** (JSON):
    ```json
    {
      "username": "user1",
      "password": "password123"
    }
    ```
*   **Response**:
    ```json
    {
      "token": "eyJhbGciOiJIUzI1..."
    }
    ```

### Registrazione
*   **URL**: `/register`
*   **Method**: `POST`
*   **Body** (JSON):
    ```json
    {
      "username": "user1",
      "password": "password123"
    }
    ```
*   **Response**: `200 OK` (se successo)

### Info Utente
*   **URL**: `/user/info`
*   **Method**: `GET`
*   **Headers**: `token: <token>`
*   **Response**:
    ```json
    {
      "username": "user1"
    }
    ```

---

## 2. Gestione Serre (Greenhouses)

### Lista Serre
*   **URL**: `/greenhouses`
*   **Method**: `GET`
*   **Headers**: `token: <token>`
*   **Response**:
    ```json
    [
      { "greenhouse_id": "GH_01", "name": "Serra 1", ... },
      ...
    ]
    ```

### Crea Serra
*   **URL**: `/greenhouses`
*   **Method**: `POST`
*   **Headers**: `token: <token>`
*   **Body** (JSON):
    ```json
    {
      "name": "Nuova Serra"
    }
    ```

### Rinomina Serra
*   **URL**: `/greenhouses`
*   **Method**: `PUT`
*   **Query Params**: `id=<greenhouse_id>`
*   **Headers**: `token: <token>`
*   **Body** (JSON):
    ```json
    {
      "name": "Nuovo Nome"
    }
    ```

### Elimina Serra
*   **URL**: `/greenhouses`
*   **Method**: `DELETE`
*   **Query Params**: `id=<greenhouse_id>`
*   **Headers**: `token: <token>`

---

## 3. Gestione Zone

### Lista Zone
*   **URL**: `/zones`
*   **Method**: `GET`
*   **Query Params**: `greenhouse_id=<greenhouse_id>`
*   **Headers**: `token: <token>`
*   **Response**:
    ```json
    [
      { "zone_id": "Z_01", "name": "Zona Pomodori", ... },
      ...
    ]
    ```

### Aggiungi Zona
*   **URL**: `/zones`
*   **Method**: `PUT`
*   **Query Params**: `greenhouse_id=<greenhouse_id>`
*   **Headers**: `token: <token>`
*   **Body** (JSON):
    ```json
    {
      "zone_id": "Z_NEW",
      "name": "Nome Zona"
    }
    ```

### Rinomina Zona
*   **URL**: `/zones`
*   **Method**: `PUT`
*   **Query Params**: `zone_id=<zone_id>`
*   **Headers**: `token: <token>`
*   **Body** (JSON):
    ```json
    {
      "name": "Nuovo Nome Zona"
    }
    ```

### Elimina (Disassocia) Zona
*   **URL**: `/zones`
*   **Method**: `PUT`
*   **Query Params**: `zone_id=<zone_id>`
*   **Headers**: `token: <token>`
*   **Body**: *Vuoto* (o senza campo `name`)

---

## 4. Strategie di Controllo

### Recupera Strategia
*   **URL**: `/zones/strategy`
*   **Method**: `GET`
*   **Query Params**: `zone_id=<zone_id>`
*   **Headers**: `token: <token>`
*   **Response**:
    ```json
    {
      "temperature": { "min": 18, "max": 25 },
      "humidity": { "min": 40, "max": 60 }
    }
    ```

### Modifica Strategia
*   **URL**: `/zones/strategy`
*   **Method**: `PUT`
*   **Query Params**: `zone_id=<zone_id>`
*   **Headers**: `token: <token>`
*   **Body** (JSON):
    ```json
    {
      "temperature": { "min": 20, "max": 24 },
      "humidity": { "min": 45, "max": 55 }
    }
    ```

---

## 5. Dispositivi e Telemetria

### Lista Dispositivi in Zona
*   **URL**: `/devices`
*   **Method**: `GET`
*   **Query Params**: `zone_id=<zone_id>`
*   **Headers**: `token: <token>`

### Stato Attuatore
*   **URL**: `/devices/status`
*   **Method**: `GET`
*   **Query Params**: `device_id=<device_id>`
*   **Headers**: `token: <token>`
*   **Response**: `{"device_id": "...", "status": true/false}`

### Storico Misure
*   **URL**: `/measurements`
*   **Method**: `GET`
*   **Query Params**:
    *   `device_id=<device_id>`
    *   `type=<measurement_type>` (es. temperature, humidity)
    *   `start=<timestamp>`
    *   `end=<timestamp>`
*   **Headers**: `token: <token>`
*   **Response**: Lista di tuple `[timestamp, valore]`

### Ultime Misure
*   **URL**: `/measurements/last`
*   **Method**: `GET`
*   **Query Params**: `device_id=<device_id>`
*   **Headers**: `token: <token>`
*   **Response**:
    ```json
    {
      "temperature": 22.5,
      "humidity": 45,
      ...
    }
    ```

### Consumi Energetici
*   **URL**: `/consumption`
*   **Method**: `GET`
*   **Query Params**:
    *   `device_id=<device_id>`
    *   `start=<timestamp>`
    *   `end=<timestamp>`
*   **Headers**: `token: <token>`
