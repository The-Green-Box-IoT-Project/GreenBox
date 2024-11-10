import time
from control_module import ControlModule
from tools.my_mqtt import MyMQTT

# Configuration
BROKER_IP = "localhost"
BROKER_PORT = 1883

# Define identifiers
client_id = "01f20b9e-6df4-43df-9fd6-c1376bb2ba41"
greenhouse_id = "greenhouse1"
raspberry_id = "rb01"  # Specific Raspberry Pi identifier
sensor_id = "dht11"
measurement_type = "temperature"

# Construct the base topic dynamically
base_topic = f"/{client_id}/{greenhouse_id}/{raspberry_id}/{sensor_id}/{measurement_type}"

TEMPERATURE_TOPIC = f"{base_topic}/statistics"
RASPBERRY_ID = raspberry_id

# Create the MQTT client
mqtt_client = MyMQTT(clientID="TemperatureControl", broker=BROKER_IP, port=BROKER_PORT)

# Create the control module for the specific Raspberry Pi
control_module = ControlModule(mqtt_client, RASPBERRY_ID, base_topic)

# Set the control module in the MQTT client
mqtt_client.set_control_module(control_module)

# Start the MQTT client and subscribe to the temperature statistics topic
mqtt_client.start()
mqtt_client.mySubscribe(TEMPERATURE_TOPIC)

# Keep the program running
try:
    while True:
        time.sleep(30)
except KeyboardInterrupt:
    print("Interruzione ricevuta, fermo il client MQTT")
    mqtt_client.stop()
