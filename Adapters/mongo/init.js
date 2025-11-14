// Adapters/mongo/init.js
const dbName = process.env.MONGO_INITDB_DATABASE || "greenbox";
const db = db.getSiblingDB(dbName);

// CREA COLLECTION GREENHOUSES
db.createCollection("greenhouses");
db.greenhouses.insertOne({
  greenhouse_id: "gh_001",
  tenant_id: "alice88",           // lo user del tuo users.json
  label: "Serra di Alice",
  location: { lat: 41.9, lon: 12.5 },
  devices: ["dev_001"],
  thresholds: {
    temperature: { lower: 20, upper: 25, deadband: 0.5 }
  },
  created_at: new Date(),
  updated_at: new Date()
});

// CREA COLLECTION DEVICES
db.createCollection("devices");
db.devices.insertOne({
  device_id: "dev_001",
  greenhouse_id: "gh_001",
  name: "Temp sensor demo",
  device_model: "DHT22",
  device_type: "sensor",
  role: "temperature_sensor",
  status: "offline",
  created_at: new Date(),
  updated_at: new Date()
});
