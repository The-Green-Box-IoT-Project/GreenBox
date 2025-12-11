import logging
import time
from dotenv import load_dotenv
from greenbox.utils.logging import setup_logger
from greenbox.statistics.statistics import StateAggregator


def main():
    """Start the statistics service (StateAggregator) and keep it alive."""
    load_dotenv()

    # Create and start the new aggregator
    aggregator = StateAggregator()
    setup_logger("statistics_aggregator")

    try:
        aggregator.start()
        # The main thread waits here, while the aggregator runs in a background thread.
        # This allows a graceful shutdown on KeyboardInterrupt (Ctrl+C).
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