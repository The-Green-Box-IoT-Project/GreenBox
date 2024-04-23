from sensors.dht11 import DHT11
from sensors.pH_meter import PH_meter
from sensors.soil_hygrometer import GrodanSens
from sensors.PAR_meter import PAR_meter
from sensors.modules.my_mqtt import *
import time

# MQTT broker configuration
broker_address = "localhost"
broker_port = 1883
client_id = "Marzio"


class RaspberryConnector:
    def __init__(self, broker_address, broker_port, client_id, seconds):

        # Elapsed between messages sent to the broker and used for resampling the original data
        self.seconds = seconds

        # Info about MQTT communication
        self.broker_address = broker_address
        self.broker_port = broker_port
        self.client_id = client_id
        self.mqtt_instance = None

        # Sensors' objects
        self.dht11 = DHT11(seconds=self.seconds)
        self.grodan = GrodanSens(seconds=self.seconds)
        self.pH_meter = PH_meter(seconds=self.seconds)
        self.PAR_meter = PAR_meter(seconds=self.seconds)

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
            print("Publisher stopped.")


if __name__ == "__main__":
    rc = RaspberryConnector(broker_address, broker_port, client_id, seconds=3)
    rc.publish(rc.dht11.temperature, rc.dht11.topic_temperature)
    rc.publish(rc.dht11.air_humidity, rc.dht11.topic_air_humidity)
    rc.publish(rc.grodan.soil_humidity, rc.grodan.topic_soil_humidity)
    rc.publish(rc.pH_meter.pH, rc.pH_meter.topic_pH)
    rc.publish(rc.PAR_meter.PAR, rc.PAR_meter.topic_PAR)

