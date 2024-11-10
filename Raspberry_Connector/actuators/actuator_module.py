import json
import time
import paho.mqtt.client as mqtt
import requests  # Import requests to handle HTTP requests

class Actuator:
    def __init__(self, client_id, broker, port, base_topic, actuator_type, catalog_url):
        """
        :param client_id: MQTT client ID to identify the actuator
        :param broker: MQTT broker IP address
        :param port: MQTT broker port
        :param base_topic: Base MQTT topic for the actuator
        :param actuator_type: Type of actuator (e.g., "cooling", "heating")
        :param catalog_url: URL of the catalog server
        """
        self.base_topic = base_topic
        self.actuator_type = actuator_type
        self._mqtt_client = mqtt.Client(client_id)
        self.broker = broker
        self.port = port
        self.catalog_url = catalog_url  # Store the catalog URL
        # Construct the command topic dynamically
        self.command_topic = f"{self.base_topic}/actuators/{actuator_type}"

        # Set MQTT callbacks
        self._mqtt_client.on_connect = self.on_connect
        self._mqtt_client.on_message = self.on_message

    def on_connect(self, client, userdata, flags, rc):
        if rc == 0:
            print(f"[INFO] Connected to MQTT broker {self.broker} successfully.")
            client.subscribe(self.command_topic)
            print(f"[INFO] Subscribed to topic: {self.command_topic}")
        else:
            print(f"[ERROR] Failed to connect to MQTT broker. Return code: {rc}")

    def on_message(self, client, userdata, message):
        payload = json.loads(message.payload.decode("utf-8"))
        command = payload.get("command")
        activate = payload.get("activate")

        if command == self.actuator_type:
            if activate:
                self.activate()
            else:
                self.deactivate()

    def activate(self):
        print(f"[ACTUATOR] {self.actuator_type.capitalize()} activated.")
        # Code to activate the actuator (hardware or simulation)
        time.sleep(2)  # Simulate activation time
        # Update the catalog with the new status
        self.update_catalog(status='active')

    def deactivate(self):
        print(f"[ACTUATOR] {self.actuator_type.capitalize()} deactivated.")
        # Code to deactivate the actuator
        # ...
        # Update the catalog with the new status
        self.update_catalog(status='inactive')

    def update_catalog(self, status):
        """
        Sends a PUT request to the catalog server to update the actuator status.

        :param status: The current status of the actuator ('active' or 'inactive')
        """
        url = f"{self.catalog_url}/actuators/{self.actuator_type}"
        data = {
            "status": status,
            "timestamp": time.time(),
            "actuator_type": self.actuator_type,
            "base_topic": self.base_topic,
            # Add any other relevant information if needed
        }

        headers = {'Content-Type': 'application/json'}

        try:
            response = requests.put(url, data=json.dumps(data), headers=headers)
            if response.status_code == 200:
                print(f"[INFO] Catalog updated successfully for {self.actuator_type} actuator.")
            else:
                print(f"[ERROR] Failed to update catalog. Status code: {response.status_code}")
        except Exception as e:
            print(f"[ERROR] Exception while updating catalog: {e}")

    def start(self):
        self._mqtt_client.connect(self.broker, self.port)
        self._mqtt_client.loop_start()

    def stop(self):
        self._mqtt_client.loop_stop()
        self._mqtt_client.disconnect()
