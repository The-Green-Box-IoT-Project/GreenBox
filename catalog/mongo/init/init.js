// Adapters/mongo/init.js

// Qui NON esiste process.env: siamo nel mongo shell, non in Node.js
// Quindi usiamo direttamente il nome del database che sappiamo già.
var dbName = "greenbox";
var db = db.getSiblingDB(dbName);

// --- PULIZIA (solo per sviluppo; non usare in produzione così) ---
db.users.drop();
db.greenhouses.drop();
db.devices.drop();

// ========== USERS ==========
db.createCollection("users");

db.users.insertMany([
  {
    username: "alice88",
    name: "Alice",
    surname: "Brambilla",
    email: "Alice@example.com",
    password: "secret",
    address: "corso Belgio 12",
    telefono: "3287580661",
    greenhouses: [
      {
        greenhouse_id: "GH_001",
        name: "My First Greenhouse"
      }
    ]
  },
  {
    username: "senpai",
    name: "Senpai",
    surname: "User",
    email: "senpai@example.com",
    password: "secret",
    address: "via Roma 45",
    telefono: "3298765432",
    greenhouses: [
      {
        greenhouse_id: "GH_002",
        name: "My First Greenhouse"
      }
    ]
  }
]);

// ========== GREENHOUSES ==========
db.createCollection("greenhouses");

db.greenhouses.insertOne({
  greenhouse_id: "GH_001",
  owner: "alice88",
  name: "SerraAlice",
  raspberry: ["rb00101"],
  actuators: ["fan01", "heater01", "irrigation01"],
  created_at: new Date(),
  updated_at: new Date()
});

// ========== DEVICES ==========
db.createCollection("devices");

db.devices.insertMany([
  {
    device_id: "rb00101",
    greenhouse_id: "GH_001",
    type: "raspberry",
    role: "controller",
    status: "offline",
    created_at: new Date(),
    updated_at: new Date()
  },
  {
    device_id: "fan01",
    greenhouse_id: "GH_001",
    type: "actuator",
    role: "fan",
    status: "offline",
    created_at: new Date(),
    updated_at: new Date()
  },
  {
    device_id: "heater01",
    greenhouse_id: "GH_001",
    type: "actuator",
    role: "heater",
    status: "offline",
    created_at: new Date(),
    updated_at: new Date()
  },
  {
    device_id: "irrigation01",
    greenhouse_id: "GH_001",
    type: "actuator",
    role: "irrigation",
    status: "offline",
    created_at: new Date(),
    updated_at: new Date()
  }
]);