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
    email: "alice88@example.com",
    greenhouses: [
      { greenhouse_id: "GH_001", name: "SerraAlice" }
    ]
  }
]);

// ========== GREENHOUSES ==========
db.createCollection("greenhouses");
db.greenhouses.insertOne({
  greenhouse_id: "GH_001",
  owner: "alice88",
  name: "SerraAlice",
  // Canonical: greenhouse keeps a flat list of device_id strings
  devices: [
    "rb00101",
    "Z_001_fan",
    "Z_001_heater",
    "Z_001_irrigation",
    "Z_001_light"
  ],
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
      light: { min: 300, max: 800 },
      airHumidity: { min: 0.40, max: 0.70 },
      soilHumidity: { min: 0.25, max: 0.45 }
    }
  },
  {
    greenhouse_id: "GH_001",
    zone_id: "Z_002",
    name: "Zona Insalata",
    // Canonical: every zone has a default strategy
    strategy: {
      temperature: { min: 20, max: 25 },
      light: { min: 300, max: 800 },
      airHumidity: { min: 0.40, max: 0.70 },
      soilHumidity: { min: 0.25, max: 0.45 }
    }
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
    device_id: "Z_001_fan",
    greenhouse_id: "GH_001",
    zone_id: "Z_001",
    type: "actuator",
    role: "fan",
    status: "off",
    name: "Fan"
  },
  {
    device_id: "Z_001_heater",
    greenhouse_id: "GH_001",
    zone_id: "Z_001",
    type: "actuator",
    role: "heater",
    status: "off",
    name: "Heater"
  },
  {
    device_id: "Z_001_irrigation",
    greenhouse_id: "GH_001",
    zone_id: "Z_001",
    type: "actuator",
    role: "irrigation",
    status: "off",
    name: "Irrigation"
  },
  {
    device_id: "Z_001_light",
    greenhouse_id: "GH_001",
    zone_id: "Z_001",
    type: "actuator",
    role: "light",
    status: "off",
    name: "Light"
  }
]);
