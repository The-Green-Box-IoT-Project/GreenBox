import logging
from dotenv import load_dotenv
import time

from statistics import StateAggregator


def main():
    """Start the statistics service (StateAggregator) and keep it alive."""
    load_dotenv()
    
    # Create and start the new aggregator
    aggregator = StateAggregator()

    try:
        aggregator.start()
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        logging.info("Interrupted, shutting down statistics aggregator...")
    finally:
        try:
            aggregator.stop()
        except Exception:
            logging.exception("Error during aggregator shutdown.")


if __name__ == "__main__":
    main()