import time
import logging
from concurrent.futures import ThreadPoolExecutor

from utils.tools import read_env, setup_logger
from raspberry import RaspberryConnector
from sensors.dht11.dht11 import DHT11, DHT11sim
from sensors.PAR_meter.PAR_meter import PAR_meter, PAR_meter_sim


read_env()
setup_logger()

raspberry = RaspberryConnector()

is_sim = True
if is_sim:
    DHT11 = DHT11sim
    PAR_meter = PAR_meter_sim
    logging.info('Sensor simulation mode enabled.')

dht11 = DHT11(broker_ip=raspberry.broker_ip, broker_port=raspberry.broker_port, parent_topic=raspberry.parent_topic)
par = PAR_meter(broker_ip=raspberry.broker_ip, broker_port=raspberry.broker_port, parent_topic=raspberry.parent_topic)


def publish_dht11_data():
    dht11.start()
    while True:
        dht11.publisher_temperature.publish(dht11.read_value())
        time.sleep(2)


def publish_par_data():
    par.start()
    while True:
        par.publisher.publish(par.read_value())
        time.sleep(2)


if __name__ == "__main__":
    with ThreadPoolExecutor(max_workers=2) as executor:  # max_workers must be equal to the number of publication tasks
        # Sends publication functions as tasks to the thread pool
        executor.submit(publish_dht11_data)
        executor.submit(publish_par_data)


