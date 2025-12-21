import logging
import time
from utils.logging import setup_logger
from controller import Controller


def main():
    """Start the control bridge (Controller) and keep it alive.""" 

    ctrl = Controller()
    setup_logger("controller")

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
