import logging
import time
from dotenv import load_dotenv
from Actuators.actuator.actuator import Actuator
from utils.tools import setup_logger


class Humidifier(Actuator):
    SYSTEM = 'humidification_system'

    def __init__(self):
        super().__init__(self.SYSTEM)
        self.device_uuid = 'humidifier_001'  # todo: elimina dopo aver collegato il catalog
        self.CMD_TOPIC = self.build_cmd_topic(self.SYSTEM, self.device_uuid)
        self.DATA_TOPIC = self.build_data_topic(self.SYSTEM, self.device_uuid)


if __name__ == '__main__':
    load_dotenv()
    setup_logger("humidifier")

    humidifier = Humidifier()
    humidifier.start()

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        logging.info(f"[{humidifier.device_uuid}] Stopping actuator...")
    finally:
        humidifier.shutdown()
