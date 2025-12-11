import argparse
import json
import logging
import time
from pathlib import Path
from dotenv import load_dotenv

from greenbox.raspberry.raspberry import RaspberryHub
from greenbox.utils.logging import setup_logger

def find_raspberry_config(raspberry_id: str, config_data: dict) -> dict:
    """
    Searches the config data to find the configuration for a specific raspberry ID.
    """
    for rb in config_data.get("raspberries", []):
        if rb.get("id") == raspberry_id:
            return rb
    return None

def main():
    """
    This script runs a single, independent Raspberry Pi instance based on its ID.
    """
    parser = argparse.ArgumentParser(description="Run a single GreenBox Raspberry Pi instance.")
    parser.add_argument("--id", type=str, required=True, help="The unique ID of the Raspberry Pi to run (e.g., 'rb_001').")
    # In the future, is_sim could also be a command-line argument
    # parser.add_argument("--sim", action="store_true", help="Run in simulation mode.")
    args = parser.parse_args()

    load_dotenv()
    setup_logger(f"raspberry_{args.id}")

    # --- Configuration Loading ---
    local_config = None
    try:
        cfg_path = Path(__file__).parent / "config.json"
        with cfg_path.open("r", encoding="utf-8") as f:
            full_config = json.load(f)
        
        local_config = find_raspberry_config(args.id, full_config)
        
        if not local_config:
            raise ValueError(f"Raspberry with id '{args.id}' not found in raspberry/config.json")

    except Exception as e:
        logging.error(f"Failed to load configuration for Raspberry '{args.id}': {e}", exc_info=True)
        return

    # --- Hub Initialization and Execution ---
    hub_instance = None
    try:
        # Toggle simulation here for now
        is_sim = True
        if is_sim:
            logging.info("Sensor simulation mode enabled.")

        hub_instance = RaspberryHub(
            raspberry_id=args.id,
            local_config=local_config,
            is_sim=is_sim
        )

        hub_instance.start()
        
        while True:
            time.sleep(5)

    except KeyboardInterrupt:
        logging.info(f"Shutdown requested for Raspberry '{args.id}'.")
    except Exception as e:
        logging.error(f"An unhandled error occurred for Raspberry '{args.id}': {e}", exc_info=True)
    finally:
        if hub_instance:
            hub_instance.stop()
        logging.info(f"Raspberry '{args.id}' has been stopped.")


if __name__ == "__main__":
    main()
