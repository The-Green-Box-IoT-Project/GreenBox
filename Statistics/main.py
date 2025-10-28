import logging
import time
from dotenv import load_dotenv
from utils.tools import setup_logger
from Statistics.statistics.statistics import StatisticsHub


def main():
    """Start the statistics (StatisticsHub) and keep it alive."""
    load_dotenv()
    setup_logger("statistics")

    hub = StatisticsHub(sim=True)  # if simulation is on else False

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
