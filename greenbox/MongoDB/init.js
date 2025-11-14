// Adapters/mongo/init/init.js
const dbName = process.env.MONGO_INITDB_DATABASE || "greenbox";
const db = db.getSiblingDB(dbName);

// GREENHOUSES
db.createCollection("greenhouses");
db.greenhouses.insertOne({
  greenhouse_id: "gh_001",
  tenant_id: "tnt_001",
  label: "Serra Demo",
  location: { lat: 41.9, lon: 12.5 },
  device_map: { ventilation_system: "fan_001" },
  thresholds: {
    temperature: { lower: 20, upper: 25, deadband: 0.5 }
  },
  created_at: new Date(),
  updated_at: new Date()
});

// RASPBERRY_CONNECTORS (devices)
db.createCollection("raspberry_connectors");
db.raspberry_connectors.insertOne({
  raspberry_id: "rb_001",
  tenant_id: "tnt_001",
  greenhouse_id: "gh_001",
  label: "RB demo",
  mqtt_client_id: "rb_001",
  status: "offline",
  allowed_topics: [],
  metadata: {},
  created_at: new Date(),
  updated_at: new Date()
});
