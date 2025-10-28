import logging
import time
from dotenv import load_dotenv
from Actuators.actuator.actuator import Actuator
from utils.tools import setup_logger


class Led(Actuator):
    SYSTEM = 'illumination_system'

    def __init__(self):
        super().__init__(self.SYSTEM)
        self.device_uuid = 'led_001'  # todo: elimina dopo aver collegato il catalog
        self.CMD_TOPIC = self.build_cmd_topic(self.SYSTEM, self.device_uuid)
        self.DATA_TOPIC = self.build_data_topic(self.SYSTEM, self.device_uuid)


if __name__ == '__main__':
    load_dotenv()
    setup_logger("led")

    led = Led()
    led.start()

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        logging.info(f"[{led.device_uuid}] Stopping actuator...")
    finally:
        led.shutdown()
        