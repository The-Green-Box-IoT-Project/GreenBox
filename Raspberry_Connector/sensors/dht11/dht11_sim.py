from time import sleep

from Raspberry_Connector.sensors.dht11.dht11 import DHT11
from Raspberry_Connector import raspberry
from Raspberry_Connector.sensors.sensor_simulator import *


class DHT11sim(DHT11):
    def __init__(self, broker_ip, broker_port, parent_topic):
        super().__init__(broker_ip, broker_port, parent_topic)

    def read_value(self):
        df_temperature = TempSensor_sim().value
        temp = SensorSimulator.read_current_value(df_temperature)
        self.publisher_temperature.publish(temp)
        print(temp)

        df_air_humidity = AirHumSensor_sim().value
        air_humidity = SensorSimulator.read_current_value(df_air_humidity)
        print(air_humidity)
        pass


if __name__ == '__main__':
    is_sim = True
    if is_sim:
        DHT11 = DHT11sim
    device_id, device_name = raspberry.retrieve_device()
    catalog_ip, catalog_port = raspberry.retrieve_catalog()
    broker_ip, broker_port = raspberry.retrieve_broker(catalog_ip, catalog_port)
    print('Broker IP: ', broker_ip)
    parent_topic = raspberry.build_parent_topic(device_id)
    sensor_dht11 = DHT11(broker_ip=broker_ip, broker_port=broker_port, parent_topic=parent_topic)
    sensor_dht11.start()
    while True:
        print(broker_ip, ':', broker_port)
        sensor_dht11.read_value()
        sleep(1)
