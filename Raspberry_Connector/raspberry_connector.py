from sensors.dht11 import TempSensor, AirHumSensor
from sensors.pH_meter import PH_meter
from sensors.soil_hygrometer import GrodanSens
from sensors.PAR_meter import PAR_meter
from Raspberry_Connector.tools.my_mqtt import *
import time
import json


class RaspberryConnector:

    def __init__(self, conf_path, devices_path):

        # Info about all sensors and actuators
        self.devices_path = devices_path
        with open(devices_path) as json_file:
            self.devices_info = json.load(json_file)

        # List of all sensors' objects
        self.sensors_list = []

        # Instantiate sensors' objects
        for sensor in self.devices_info["resources"]["sensors"]:
            if sensor["device_name"] == "DHT11":
                self.temp_sens = TempSensor(sensor)
                self.air_hum_sens = AirHumSensor(sensor)
                self.sensors_list.append(self.temp_sens)
                self.sensors_list.append(self.air_hum_sens)
            elif sensor["device_name"] == "pH_meter":
                self.pH_meter = PH_meter(sensor)
                self.sensors_list.append(self.pH_meter)
            elif sensor["device_name"] == "PAR_meter":
                self.PAR_meter = PAR_meter(sensor)
                self.sensors_list.append(self.PAR_meter)
            elif sensor["device_name"] == "Grodan":
                self.grodan = GrodanSens(sensor)
                self.sensors_list.append(self.grodan)

        # Instantiate actuator's object
        # //////////////////////////// #

        # Info about MQTT communication
        self.conf_path = conf_path
        with open(conf_path) as json_file:
            self.conf_info = json.load(json_file)
        self.broker_address = self.conf_info["ip"]
        self.broker_port = self.conf_info["port"]
        self.client_id = self.conf_info["clientID"]

        # Creates and the MQTT client
        self.mqtt_client = MyMQTT(
            clientID=self.client_id,
            broker=self.broker_address,
            port=self.broker_port
        )

        # Start the connection to the broker
        self.mqtt_client.start()

        # Subscription to MQTT topics
        # self.subscribe_to_topics()

    def collect_measurements(self, count=0):
        measurements = []
        for sensor in self.sensors_list:
            meas = {
                "topic": sensor.topic,
                "data": {
                    sensor.field: sensor.value.iloc[count]
                }
            }
            measurements.append((meas, sensor.seconds))
        return measurements

    def publish_measurement(self, sensor):
        try:
            index = 0
            while True:
                data = {sensor.field: sensor.value.iloc[index]}
                self.mqtt_client.myPublish(sensor.topic, data)
                time.sleep(sensor.seconds)
                index += 1
        except KeyboardInterrupt:
            print("Stopping publisher...")
            self.mqtt_client.stop()
            print("Publisher stopped.")

    def publish(self, sensor):
        # Start the connection to the broker
        self.mqtt_client.start()
        self.publish_measurement(sensor)

    def subscribe_to_topics(self):
        """Subscription to MQTT topics"""
        for end_det in self.devices_info["endpoints_details"]:
            if end_det.get("endpoint") == "MQTT":
                self._topic = end_det["topics"]

        for topic in self._topic:
            self.mqtt_client.mySubscribe(topic)
            while True:
                pass

    def publish_last_measurement(self):
        """Publishes sensors' data"""
        try:
            index = 0
            while True:
                for measurement in self.collect_measurements(index):
                    self.mqtt_client.myPublish(measurement[0]["topic"], measurement[0]["data"])
                    time.sleep(measurement[1])
                    index += 1

        except KeyboardInterrupt:
            print("Stopping publisher...")
            self.mqtt_client.stop()
            print("Publisher stopped.")


if "__main__" == __name__:
    rc = RaspberryConnector("conf.json", "devices.json")
    rc.publish_last_measurement()
