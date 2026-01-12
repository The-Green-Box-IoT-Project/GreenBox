# Catalog API Endpoints

Base URL: `http://localhost:8484`

Auth header (all except register/login): `token: <TOKEN>`

## Auth
- POST `/register` (no token)
  - Body JSON:
    - `{"username":"<USER>","password":"<PASS>","email":"<EMAIL>"}`
- POST `/login` (no token)
  - Body JSON:
    - `{"username":"<USER>","password":"<PASS>"}`
  - Response: `{"token":"..."}`

## User
- GET `/user/info`

## Greenhouses
- GET `/greenhouses`
- POST `/greenhouses`
  - Body JSON: `{"name":"<GREENHOUSE_NAME>"}`
- PUT `/greenhouses?id=<GH_ID>`
  - Body JSON: `{"name":"<NEW_NAME>"}`
- DELETE `/greenhouses?id=<GH_ID>`

## Zones
- GET `/zones?greenhouse_id=<GH_ID>`
- PUT `/zones/validate`
  - Body JSON: `{"zone_id":"<ZONE_ID>"}`
- PUT `/zones?greenhouse_id=<GH_ID>`
  - Body JSON: `{"zone_id":"<ZONE_ID>","name":"<ZONE_NAME>"}`
- PUT `/zones?zone_id=<ZONE_ID>`
  - Body JSON: `{"name":"<NEW_NAME>"}`
- PUT `/zones?zone_id=<ZONE_ID>`
  - No body (disassociate zone)

## Control Strategy
- GET `/zones/strategy?zone_id=<ZONE_ID>`
- PUT `/zones/strategy?zone_id=<ZONE_ID>`
  - Body JSON example:
    - `{"temperature":{"min":8,"max":30},"soilHumidity":0.2,"airHumidity":{"min":0.1,"max":0.9},"light":{"enabled":true,"timeRange":{"start":9,"end":17}}}`

## Devices
- GET `/devices?zone_id=<ZONE_ID>`
- GET `/devices/status?device_id=<DEVICE_ID>`

## Measurements (raspberry only)
- GET `/measurements?device_id=<RB_ID>&type=<TYPE>&start=<S>&end=<E>`
  - TYPE allowed: `temperature`, `humidity`, `light`, `soil_humidity`, `airHumidity`,
    `soilHumidity`, `illuminance`, `ph`
  - `start`/`end` can be numeric or ISO-8601; if both present and start > end, returns 400.
- GET `/measurements/last?device_id=<RB_ID>`

## Consumption (actuators)
- GET `/consumption?device_id=<ACTUATOR_ID>&start=<S>&end=<E>`
  - Returns list of `[time, value]` (max 60 values, aggregated mean).
