import json
import os
from pathlib import Path
import time
import requests
from dotenv import load_dotenv

from utils.my_mqtt import MyMQTT

P = Path(__file__).parent.absolute()
CONFIG_FILE = P / 'config.json'
CATALOG_FILE = P / 'catalog.json'

load_dotenv()
greenbox_uuid = os.getenv('GREENBOX_UUID')


def retrieve_catalog():
    with open(CATALOG_FILE, 'r') as f:
        data = json.load(f)
        catalog_ip = data['catalog_ip']
        catalog_port = data['catalog_port']
        return catalog_ip, catalog_port


def retrieve_device():
    with open(CONFIG_FILE, 'r') as f:
        data = json.load(f)
        device_id = data['device_id']
        device_name = data['device_name']
    return device_id, device_name


def retrieve_broker(catalog_ip, catalog_port):
    url = 'http://' + catalog_ip + ':' + str(catalog_port) + '/broker'
    broker_data = json.loads(requests.get(url).text)
    broker_ip = broker_data['broker_ip']
    broker_port = broker_data['broker_port']
    return broker_ip, int(broker_port)


def build_parent_topic(device_id):
    return f"""/{greenbox_uuid}/greenhouse1/{device_id}"""


class RaspberryConnector:

    def __init__(self):

        (self.device_id,
         self.device_name) = retrieve_device()

        (self.catalog_ip,
         self.catalog_port) = retrieve_catalog()

        (self.broker_ip,
         self.broker_port) = retrieve_broker(self.catalog_ip, self.catalog_port)

        self.parent_topic = build_parent_topic(self.device_id)

    def connect_to_broker(self, client_id, topic):

        # Creates the MQTT client
        self.mqtt_client = MyMQTT(
            clientID=client_id,
            topic=topic,
            broker=self.broker_ip,
            port=self.broker_port,
        )

        # Start the connection to the broker
        self.mqtt_client.start()

    def publish_measurement(self, topic, message):
        try:
            while True:
                self.mqtt_client.myPublish(topic, message)
                time.sleep(3)
        except KeyboardInterrupt:
            print("Stopping publisher...")
            self.mqtt_client.stop()
            print("Publisher stopped.")
