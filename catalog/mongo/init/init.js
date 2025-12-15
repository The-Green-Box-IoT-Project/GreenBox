// Adapters/mongo/init.js

var dbName = "greenbox";
var db = db.getSiblingDB(dbName);

// --- PULIZIA ---
db.users.drop();
db.greenhouses.drop();
db.devices.drop();
db.zones.drop(); // Nuova collezione

// ========== USERS ==========
db.createCollection("users");
db.users.insertMany([
  {
    username: "alice88",
    password: "secret",
    greenhouses: ["GH_001"]
  }
]);

// ========== GREENHOUSES ==========
db.createCollection("greenhouses");
db.greenhouses.insertOne({
  greenhouse_id: "GH_001",
  owner: "alice88",
  name: "SerraAlice",
  // Il nuovo codice si aspetta una lista unica 'devices', non separata
  devices: ["rb00101", "fan01", "heater01", "irrigation01"], 
  created_at: new Date(),
  updated_at: new Date()
});

// ========== ZONES (NUOVO) ==========
db.createCollection("zones");
db.zones.insertMany([
  {
    greenhouse_id: "GH_001",
    zone_id: "Z_001",
    name: "Zona Pomodori",
    strategy: {
        temperature: { min: 20, max: 25 },
        humidity: { min: 40, max: 60 }
    }
  },
  {
    greenhouse_id: "GH_001",
    zone_id: "Z_002",
    name: "Zona Insalata",
    strategy: {}
  }
]);

// ========== DEVICES ==========
db.createCollection("devices");
db.devices.insertMany([
  {
    device_id: "rb00101",
    greenhouse_id: "GH_001",
    zone_id: "Z_001", // Associato a una zona
    type: "raspberry",
    role: "controller",
    status: "online",
    name: "Main Controller"
  },
  {
    device_id: "fan01",
    greenhouse_id: "GH_001",
    zone_id: "Z_001",
    type: "actuator",
    role: "ventilation_system",
    status: "off",
    name: "Ventola Principale"
  },
  {
    device_id: "heater01",
    greenhouse_id: "GH_001",
    zone_id: "Z_002",
    type: "actuator",
    role: "heating_system",
    status: "on",
    name: "Riscaldamento"
  }
]);
