import argparse
import json
import logging
import time
from pathlib import Path
from dotenv import load_dotenv

from greenbox.actuators.actuators import Actuator
from greenbox.utils.catalog_client import get_broker_info # Changed import
from greenbox.utils.logging import setup_logger


def find_actuator_config(actuator_id: str, config_data: dict) -> dict:
    """
    Searches the hierarchical config data to find the configuration
    for a specific actuator ID.
    Returns a dictionary with gh_id, rb_id, and actuator type.
    """
    for greenhouse in config_data.get("greenhouses", []):
        gh_id = greenhouse.get("id")
        for raspberry in greenhouse.get("raspberries", []):
            rb_id = raspberry.get("id")
            for actuator in raspberry.get("actuators", []):
                if actuator.get("id") == actuator_id:
                    return {
                        "gh_id": gh_id,
                        "rb_id": rb_id,
                        "type": actuator.get("type"),
                    }
    return None


def main():
    """
    This script runs a single, independent actuator instance based on its ID.
    It finds its own configuration (zone, type) from the config.json file.
    """
    # --- Argument Parsing ---
    parser = argparse.ArgumentParser(
        description="Run a single GreenBox actuator instance."
    )
    parser.add_argument(
        "--id",
        type=str,
        required=True,
        help="The unique ID of the actuator to run (e.g., 'fan_001').",
    )
    args = parser.parse_args()

    load_dotenv()

    # --- Logging Setup ---
    # Each actuator process gets its own dedicated log file.
    setup_logger(f"actuator_{args.id}")

    # --- Configuration Loading ---
    actuator_config = None
    try:
        cfg_path = Path(__file__).parent / "config.json"
        with cfg_path.open("r", encoding="utf-8") as f:
            full_config = json.load(f)

        actuator_config = find_actuator_config(args.id, full_config)

        if not actuator_config:
            raise ValueError(f"Actuator with id '{args.id}' not found in config.json")

    except Exception as e:
        logging.error(
            f"Failed to load configuration for actuator '{args.id}': {e}", exc_info=True
        )
        return

    # --- Broker Info ---
    try:
        broker_ip, broker_port = get_broker_info()
    except Exception as e:
        logging.error(
            f"Could not retrieve broker info from catalog: {e}", exc_info=True
        )
        return

    # --- Actuator Initialization and Execution ---
    actuator_instance = None
    try:
        gh_id = actuator_config["gh_id"]
        rb_id = actuator_config["rb_id"]
        actuator_type = actuator_config["type"]

        # The unique client ID for MQTT can be more specific
        mqtt_client_id = f"{args.id}_{rb_id}"

        actuator_instance = Actuator(
            device_id=mqtt_client_id,
            system=actuator_type,
            gh_id=gh_id,
            rb_id=rb_id,
            broker_ip=broker_ip,
            broker_port=broker_port,
        )

        actuator_instance.start()

        while True:
            time.sleep(5)

    except KeyboardInterrupt:
        logging.info(f"Shutdown requested for actuator '{args.id}'.")
    except Exception as e:
        logging.error(
            f"An unhandled error occurred for actuator '{args.id}': {e}", exc_info=True
        )
    finally:
        if actuator_instance:
            actuator_instance.stop()
        logging.info(f"Actuator '{args.id}' has been stopped.")


if __name__ == "__main__":
    main()
