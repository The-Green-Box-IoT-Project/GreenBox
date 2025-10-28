import logging
import time
from dotenv import load_dotenv
from utils.tools import setup_logger
from Optimizer.optimizer.controller import Controller


def main():
    """Start the control bridge (Controller) and keep it alive."""
    load_dotenv()
    setup_logger("controls")

    ctrl = Controller()

    try:
        ctrl.start()
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        logging.info("Interrupted, shutting down controller...")
    finally:
        try:
            ctrl.stop()
        except Exception:
            pass


if __name__ == "__main__":
    main()
