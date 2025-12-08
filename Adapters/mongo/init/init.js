// Adapters/mongo/init.js
const dbName = process.env.MONGO_INITDB_DATABASE || "greenbox";
const targetDb = db.getSiblingDB(dbName);

// CREA COLLECTION GREENHOUSES
targetDb.createCollection("greenhouses");
targetDb.greenhouses.insertOne({
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
targetDb.createCollection("devices");
targetDb.devices.insertOne({
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

// Controller/Raspberry di esempio per test misure
targetDb.devices.insertOne({
  device_id: "rb_controller_001",
  greenhouse_id: "gh_001",
  name: "Raspberry Controller 001",
  device_model: "Pi4",
  device_type: "controller",
  role: "controller",
  status: "online",
  created_at: new Date(),
  updated_at: new Date()
});

// USERS
targetDb.createCollection("users");
targetDb.users.insertMany([
  {
    user_id: "alice88",
    name: "Alice",
    surname: "Brambilla",
    country: "IT",
    email: "alice@example.com",
    account_level: "standard"
  }
]);

// TELEMETRY (opzionale)
targetDb.createCollection("telemetry");
targetDb.telemetry.insertOne({
  device_id: "rb_controller_001",
  metrics: {
    temperature: {
      "1h": [
        { ts: "2024-06-01T10:00:00Z", value: 24.1 },
        { ts: "2024-06-01T10:10:00Z", value: 24.3 },
        { ts: "2024-06-01T10:20:00Z", value: 24.0 },
        { ts: "2024-06-01T10:30:00Z", value: 23.9 },
        { ts: "2024-06-01T10:40:00Z", value: 24.2 }
      ],
      "1d": [
        { ts: "2024-05-31T12:00:00Z", value: 23.5 },
        { ts: "2024-05-31T18:00:00Z", value: 23.9 },
        { ts: "2024-06-01T00:00:00Z", value: 24.0 },
        { ts: "2024-06-01T06:00:00Z", value: 24.4 }
      ]
    },
    humidity: {
      "1h": [
        { ts: "2024-06-01T10:00:00Z", value: 68.0 },
        { ts: "2024-06-01T10:10:00Z", value: 67.5 },
        { ts: "2024-06-01T10:20:00Z", value: 67.0 },
        { ts: "2024-06-01T10:30:00Z", value: 66.8 }
      ]
    }
  },
  created_at: new Date(),
  updated_at: new Date()
});

// CREA COLLECTION GREENHOUSE_EFFECTS (modelli attuatori per serra)
targetDb.createCollection("greenhouse_effects");
targetDb.greenhouse_effects.insertOne({
  greenhouse_id: "gh_001",
  effects: [
    { system: "ventilation_system", level: "50%", temperature: -0.0083, humidity: -0.0833 },
    { system: "ventilation_system", level: "100%", temperature: -0.0167, humidity: -0.1667 },
    { system: "heating_system", level: "100%", temperature: 0.0167, humidity: 0.0833, soil_humidity: -0.00333 },
    { system: "illumination_system", level: "100%", light: 500.0, temperature: 0.00008 }
  ],
  created_at: new Date(),
  updated_at: new Date()
});
