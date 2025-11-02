import logging
import time
from dotenv import load_dotenv
from greenbox.utils.logging import setup_logger
from greenbox.statistics.statistics import StatisticsHub


def main():
    """Start the statistics (StatisticsHub) and keep it alive."""
    load_dotenv()

    hub = StatisticsHub(sim=True)  # if simulation is on else False
    setup_logger(f"stats_{hub.workers[0].raspberry_id}")

    try:
        hub.start()
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        logging.info("Interrupted, shutting down statistics...")
    finally:
        try:
            hub.stop()
        except Exception:
            pass


if __name__ == "__main__":
    main()
