from pathlib import Path

from Raspberry_Connector.sensors import sensors_interface
from Raspberry_Connector import raspberry

P = Path(__file__).parent.absolute()
CONFIG_FILE = P / 'config.json'


class DHT11:
    def __init__(self, broker_ip, broker_port, parent_topic):
        super().__init__()
        self.device_id, self.device_name, self.device_pin, measurements = sensors_interface.retrieve_sensor(CONFIG_FILE)
        self.measurements = measurements
        # TODO: publisher


if __name__ == '__main__':
    broker_ip, broker_port = raspberry.retrieve_broker()
    device_id, device_name = raspberry.retrieve_device()
    catalog_ip, catalog_port = raspberry.retrieve_catalog()
    # TODO: parent topic build
    DHT11(broker_ip=broker_ip, broker_port=broker_port, parent_topic='')
