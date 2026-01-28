// Adapters/mongo/init.js

var dbName = "greenbox";
var db = db.getSiblingDB(dbName);

// =========================
// PULIZIA (reset completo)
// =========================
db.users.drop();
db.greenhouses.drop();
db.zones.drop();
db.devices.drop();
db.counters.drop();

// =========================
// USERS
// =========================
db.createCollection("users");

// UNIQUE username
db.users.createIndex({ username: 1 }, { unique: true });

db.users.insertOne({
  username: "Greenuser",
  password: "Password00",
  greenhouses: ["GH_001"]
});

// =========================
// GREENHOUSES
// =========================
db.createCollection("greenhouses");

// UNIQUE greenhouse_id
db.greenhouses.createIndex({ greenhouse_id: 1 }, { unique: true });

db.greenhouses.insertOne({
  greenhouse_id: "GH_001",
  name: "Terrace",
  zones: ["ZONE_001", "ZONE_002"]
});

// =========================
// ZONES
// =========================
db.createCollection("zones");

// UNIQUE zone_id
db.zones.createIndex({ zone_id: 1 }, { unique: true });

db.zones.insertMany([
  {
    zone_id: "ZONE_001",
    name: "Zona Pomodori",
    strategy: {
      temperature: { min: 20, max: 25 },
      light: { enabled: "false", start: 10, end: 15 },
      humidity: { min: 0.4, max: 0.7 },
      soil_humidity: { min: 0.25, max: 1.0 }
    },
    devices: [
      "RB_001",
      "VENT_001",
      "HEAT_001",
      "LIGHT_001",
      "IRRIG_001",
      "HUM_001"
    ]
  },
  {
    zone_id: "ZONE_002",
    name: "Zona Insalata",
    strategy: {
      temperature: { min: 20, max: 25 },
      light: { enabled: "true", start: 10, end: 15 },
      humidity: { min: 0.4, max: 0.7 },
      soil_humidity: { min: 0.25, max: 1.0 }
    },
    devices: [
      "RB_002",
      "VENT_002",
      "HEAT_002",
      "IRRIG_002",
      "LIGHT_002",
      "HUM_002"
    ]
  }
]);

// =========================
// DEVICES
// =========================
db.createCollection("devices");

// UNIQUE device_id
db.devices.createIndex({ device_id: 1 }, { unique: true });

db.devices.insertMany([
  // Zona 1
  { device_id: "RB_001", type: "raspberry" },
  { device_id: "VENT_001", type: "ventilation_system" },
  { device_id: "HEAT_001", type: "heating_system" },
  { device_id: "LIGHT_001", type: "illumination_system" },
  { device_id: "IRRIG_001", type: "irrigation_system" },
  { device_id: "HUM_001", type: "humidification_system" },

  // Zona 2
  { device_id: "RB_002", type: "raspberry" },
  { device_id: "VENT_002", type: "ventilation_system" },
  { device_id: "HEAT_002", type: "heating_system" },
  { device_id: "IRRIG_002", type: "irrigation_system" },
  { device_id: "LIGHT_002", type: "illumination_system" },
  { device_id: "HUM_002", type: "humidification_system" }
]);

// =========================
// COUNTERS (per ID atomici)
// =========================
db.createCollection("counters");

// Contatore greenhouse: esiste già GH_001 → prossimo = GH_002
db.counters.insertOne({
  _id: "greenhouse_seq",
  seq: 1
});
