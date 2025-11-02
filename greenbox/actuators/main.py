import logging
import time
from dotenv import load_dotenv

from greenbox.actuators.actuators import ActuatorConnector
from greenbox.utils.logging import setup_logger


def run():
    load_dotenv()
    act = ActuatorConnector()
    setup_logger(f"actuators_{act.greenhouse_id}")
    act.start()
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        logging.info(f"Stopping actuators...")
    finally:
        act.stop()


if __name__ == "__main__":
    run()
