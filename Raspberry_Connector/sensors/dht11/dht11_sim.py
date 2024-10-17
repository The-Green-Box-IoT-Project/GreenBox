from Raspberry_Connector.sensors.dht11.dht11 import DHT11


class DHT11sim(DHT11):
    def __init__(self, parent_topic, server_ip, port):
        super().__init__(parent_topic, server_ip, port)