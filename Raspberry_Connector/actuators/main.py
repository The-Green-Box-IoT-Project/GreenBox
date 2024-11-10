from actuator_module import Actuator
import time

# Configuration of the MQTT broker and metric
BROKER_IP = "localhost"
BROKER_PORT = 1883

# Define identifiers
client_id = "01f20b9e-6df4-43df-9fd6-c1376bb2ba41"
greenhouse_id = "greenhouse1"
raspberry_id = "rb01"
sensor_id = "dht11"
measurement_type = "temperature"

# Construct the base topic dynamically
base_topic = f"/{client_id}/{greenhouse_id}/{raspberry_id}/{sensor_id}/{measurement_type}"

# Catalog server URL
CATALOG_URL = "http://localhost:5123"  # Replace with your actual catalog server URL

# Create instances of actuators for "cooling" and "heating"
cooling_actuator = Actuator(
    client_id="CoolingActuator",
    broker=BROKER_IP,
    port=BROKER_PORT,
    base_topic=base_topic,
    actuator_type="cooling",
    catalog_url=CATALOG_URL
)

heating_actuator = Actuator(
    client_id="HeatingActuator",
    broker=BROKER_IP,
    port=BROKER_PORT,
    base_topic=base_topic,
    actuator_type="heating",
    catalog_url=CATALOG_URL
)

# Start both actuators
cooling_actuator.start()
heating_actuator.start()

# Keep the program running and verify operation
try:
    print("Heating and cooling systems started.")
    while True:
        time.sleep(1)
except KeyboardInterrupt:
    print("Manual interruption, shutting down.")
    cooling_actuator.stop()
    heating_actuator.stop()
