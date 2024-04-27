from sensors.dht11 import DHT11
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
            print("Publisher stopped.")


if __name__ == "__main__":
    rc = RaspberryConnector(conf_path="conf.json", devices_path="devices.json", seconds=3)
    rc.publish_last_measurements()
