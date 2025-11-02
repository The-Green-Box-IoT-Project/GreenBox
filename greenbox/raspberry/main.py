import logging
import time
from dotenv import load_dotenv
from greenbox.utils.logging import setup_logger

from greenbox.raspberry.raspberry import RaspberryHub


def main():
    """Start the raspberry (RaspberryHub) and keep it alive."""
    load_dotenv()

    # Toggle simulation here
    is_sim = True
    if is_sim:
        logging.info("Sensor simulation mode enabled.")

    hub = RaspberryHub(is_sim=is_sim)
    setup_logger(hub.raspberry_id)

    try:
        hub.start()
        # Block on workers; Ctrl+C triggers graceful shutdown
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        logging.info("Interrupted by user, shutting down...")
    finally:
        try:
            hub.stop()
        except Exception:
            pass


if __name__ == "__main__":
    main()
