import logging
from concurrent.futures import ThreadPoolExecutor

from utils.tools import read_env, setup_logger
from raspberry import RaspberryConnector
from sensors.dht11.dht11 import DHT11, DHT11sim
from sensors.PAR_meter.PAR_meter import PAR_meter, PAR_meter_sim
from sensors.pH_meter.pH_meter import pH_meter, pH_meter_sim
from sensors.soil_hygrometer.grodan import GrodanSens, GrodanSens_sim


read_env()
setup_logger()

raspberry = RaspberryConnector()

is_sim = True
if is_sim:
    DHT11 = DHT11sim
    PAR_meter = PAR_meter_sim
    pH_meter = pH_meter_sim
    GrodanSens = GrodanSens_sim
    logging.info('Sensor simulation mode enabled.')

dht11 = DHT11(broker_ip=raspberry.broker_ip, broker_port=raspberry.broker_port, parent_topic=raspberry.parent_topic)
par = PAR_meter(broker_ip=raspberry.broker_ip, broker_port=raspberry.broker_port, parent_topic=raspberry.parent_topic)
ph = pH_meter(broker_ip=raspberry.broker_ip, broker_port=raspberry.broker_port, parent_topic=raspberry.parent_topic)
grodan = GrodanSens(broker_ip=raspberry.broker_ip, broker_port=raspberry.broker_port, parent_topic=raspberry.parent_topic)


if __name__ == "__main__":
    with ThreadPoolExecutor(max_workers=4) as executor:  # max_workers must be equal to the number of publication tasks
        # Sends publication functions as tasks to the thread pool
        executor.submit(dht11.read_value)
        executor.submit(par.read_value)
        executor.submit(ph.read_value)
        executor.submit(grodan.read_value)
