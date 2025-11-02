import logging
import time
from dotenv import load_dotenv
from greenbox.utils.logging import setup_logger
from greenbox.controller.controller import Controller


def main():
    """Start the control bridge (Controller) and keep it alive."""
    load_dotenv()

    ctrl = Controller()
    setup_logger(f"ctrl_{ctrl.greenhouse_id}")

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
