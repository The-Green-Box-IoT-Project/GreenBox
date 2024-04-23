from sensors.dht11 import DHT11
<<<<<<< HEAD
from sensors.pH_meter import PH_meter
from sensors.soil_hygrometer import GrodanSens
from sensors.PAR_meter import PAR_meter
from Raspberry_Connector.tools.my_mqtt import *
import time
import json
import sys


class RaspberryConnector:

    def __init__(self, conf_path, devices_path, seconds=10):

        # Elapsed between messages sent to the broker and used for resampling the original data
        self.seconds = seconds

        # Info about all sensors and actuators
        self.devices_path = devices_path
        with open(devices_path) as json_file:
            self.devices_info = json.load(json_file)

        # List of all sensors' objects
        self.sensors_list = []
        self.list_of_last_measurement = []

        # Instantiate sensors' objects
        for sensor in self.devices_info["resources"]["sensors"]:
            if sensor["device_name"] == "DHT11":
                self.dht11 = DHT11(conf=sensor, seconds=self.seconds)
                measurement = {
                    "topic": self.dht11.topic_temperature,
                    "data_json": {self.dht11.temperature.name: self.dht11.temperature}
                }
                self.list_of_last_measurement.append(measurement)
                measurement = {
                    "topic": self.dht11.topic_air_humidity,
                    "data_json": {self.dht11.air_humidity.name: self.dht11.air_humidity}
                }
                self.list_of_last_measurement.append(measurement)
            elif sensor["device_name"] == "pH_meter":
                self.pH_meter = PH_meter(conf=sensor, seconds=self.seconds)
                measurement = {
                    "topic": self.pH_meter.topic,
                    "data_json": {self.pH_meter.pH.name: self.pH_meter.pH}
                }
                self.list_of_last_measurement.append(measurement)
            elif sensor["device_name"] == "PAR_meter":
                self.PAR_meter = PAR_meter(conf=sensor, seconds=self.seconds)
                measurement = {
                    "topic": self.PAR_meter.topic,
                    "data_json": {self.PAR_meter.PAR.name: self.PAR_meter.PAR}
                }
                self.list_of_last_measurement.append(measurement)
            elif sensor["device_name"] == "Grodan":
                self.grodan = GrodanSens(conf=sensor, seconds=self.seconds)
                measurement = {
                    "topic": self.grodan.topic,
                    "data_json": {self.grodan.soil_humidity.name: self.grodan.soil_humidity}
                }
                self.list_of_last_measurement.append(measurement)
            self.sensors_list.append(sensor)

        # Instantiate actuator's object
        # //////////////////////////// #

        # Info about MQTT communication
        self.conf_path = conf_path
        with open(conf_path) as json_file:
            self.conf_info = json.load(json_file)
        self.broker_address = self.conf_info["ip"]
        self.broker_port = self.conf_info["port"]
        self.client_id = self.conf_info["clientID"]

        # Creates and connects to the MQTT client
        self.mqtt_client = MyMQTT(
            clientID=self.client_id,
            broker=self.broker_address,
            port=self.broker_port
        )

        # Subscription to MQTT topics
        # self.subscribe_to_topics()

    def subscribe_to_topics(self):
        """Subscription to MQTT topics"""
        for end_det in self.devices_info["endpoints_details"]:
            if end_det.get("endpoint") == "MQTT":
                self._topic = end_det["topics"]

        for topic in self._topic:
            self.mqtt_client.mySubscribe(topic)
            while True:
                pass

    def publish_last_measurements(self):
        """Publishes sensors' data"""
        try:
            index = 0
            while True:
                # for measurement in self.list_of_last_measurement:
                # print(self.list_of_last_measurement)
                # measurement = self.list_of_last_measurement[0]
                # print(measurement)
                # data = list(measurement["data_json"].values())[index]
                # print(data)
                measurement = {self.dht11.temperature.name: self.dht11.temperature.iloc[index]}
                self.mqtt_client.myPublish("GreenBox/d1/s1/temperature", measurement)
                time.sleep(self.seconds)
                index += 1
                # self.list_of_last_measurement.clear()

        except KeyboardInterrupt:
            print("Stopping publisher...")
            self.mqtt_client.stop()
=======
from sensors.modules.my_mqtt import *
import time

# MQTT broker configuration
broker_address = "localhost"
broker_port = 1883
client_id = "Marzio"


class RaspberryConnector:
    def __init__(self, broker_address, broker_port, client_id, seconds):

        self.broker_address = broker_address
        self.broker_port = broker_port
        self.client_id = client_id
        self.seconds = seconds
        self.dht11 = DHT11(seconds=self.seconds)
        self.mqtt_instance = None

    def create_mqtt_instance(self):
        """Creates and connects to the MQTT client"""
        if self.mqtt_instance is None:
            self.mqtt_instance = MyMQTT(self.client_id, self.broker_address, self.broker_port)
            self.mqtt_instance.start()

    def publish(self, data, topic="sensor/data"):
        """Publishes sensors' data"""
        self.create_mqtt_instance()

        try:
            index = 0
            while True:
                data_json = {data.name: data.iloc[index]}
                self.mqtt_instance.myPublish(topic, data_json)
                print("Data sent:", data_json)
                time.sleep(self.seconds)
                index += 1

        except KeyboardInterrupt:
            print("Stopping publisher...")
            if self.mqtt_instance:  # Check if instance exists before stopping
                self.mqtt_instance.stop()
>>>>>>> 00ef6ca (Created DHT11 and Grodan sensors objects.)
            print("Publisher stopped.")


if __name__ == "__main__":
<<<<<<< HEAD
    rc = RaspberryConnector(conf_path="conf.json", devices_path="devices.json", seconds=3)
    rc.publish_last_measurements()
=======
    rc = RaspberryConnector(broker_address, broker_port, client_id, seconds=5)
    rc.publish(rc.dht11.temperature)
>>>>>>> 00ef6ca (Created DHT11 and Grodan sensors objects.)
