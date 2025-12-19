# GreenBox Catalog (Mongo-only) — Tested Endpoints

This document lists the Catalog HTTP endpoints verified end-to-end against the Mongo stack (mongo + mongo-adapter + catalog).

## Auth
- `POST /register` (no token)
  - Body: `{ "username": string, "password": string, "email": string }`
  - Expected: `200` on success, `409` if username already exists
- `POST /login` (no token)
  - Body: `{ "username": string, "password": string }`
  - Expected: `200` with `{ "token": string }`
- `GET /user/info` (token required)
  - Header: `token: <token>`
  - Expected: `200` with `{ "username": string }`

## Greenhouses
- `POST /greenhouses` (token required)
  - Header: `token: <token>`
  - Body: `{ "name": string }`
  - Expected: `200`
- `GET /greenhouses` (token required)
  - Header: `token: <token>`
  - Expected: `200` with list of `{ "id": greenhouse_id, "name": string }`
- `PUT /greenhouses?id=<greenhouse_id>&name=<new_name>` (token required)
  - Header: `token: <token>`
  - Expected: `200`, `403` if not owner
- `DELETE /greenhouses?id=<greenhouse_id>` (token required)
  - Header: `token: <token>`
  - Expected: `200`, `403` if not owner

## Zones
- `PUT /zones?greenhouse_id=<greenhouse_id>` (token required)
  - Header: `token: <token>`
  - Body: `{ "zone_id": string, "name": string }`
  - Side-effects (Mongo-only contract):
    - creates the zone with a default `strategy` (nested min/max)
    - auto-creates 4 actuator devices for the zone: `fan/heater/irrigation/light`
  - Expected: `200`
- `GET /zones?greenhouse_id=<greenhouse_id>` (token required)
  - Header: `token: <token>`
  - Expected: `200` with list of `{ "id": zone_id, "name": string }`
- `PUT /zones/validate?zone_id=<zone_id>` (token required)
  - Header: `token: <token>`
  - Expected: `200` with boolean
- `PUT /zones?zone_id=<zone_id>&name=<new_name>` (token required)
  - Header: `token: <token>`
  - Expected: `200`, `403` if not owner
- `DELETE /zones?zone_id=<zone_id>` (token required)
  - Header: `token: <token>`
  - Expected: `200`, `403` if not owner

## Strategy
- `GET /zones/strategy?zone_id=<zone_id>` (token required)
  - Header: `token: <token>`
  - Expected: `200` returning a nested object `{ metric: { min, max } }`
- `PUT /zones/strategy?zone_id=<zone_id>` (token required)
  - Header: `token: <token>`
  - Body (canonical):
    ```json
    {
      "temperature": {"min": 18, "max": 26},
      "light": {"min": 300, "max": 800},
      "airHumidity": {"min": 0.40, "max": 0.70},
      "soilHumidity": {"min": 0.25, "max": 0.45}
    }
    ```
  - Also accepted (legacy): `min_temperature`, `max_temperature`, etc.
  - Expected: `200`

## Devices
- `GET /devices?zone_id=<zone_id>` (token required)
  - Header: `token: <token>`
  - Expected: `200` with list of `{ "id": device_id, "type": string }`
- `GET /devices/status?device_id=<device_id>` (token required)
  - Header: `token: <token>`
  - Expected: `200` with `{ "device_id": string, "status": boolean }`
  - Errors: `400 not_an_actuator` if device is not an actuator

## Notes
- Endpoints under `measurements/*` and `consumption` exist but are Influx-backed; they are not included in the Mongo-only tested list.
