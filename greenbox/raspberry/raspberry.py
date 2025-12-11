from pprint import pformat
from concurrent.futures import ThreadPoolExecutor
import logging
from typing import Dict, Any

from greenbox.raspberry.sensors import Sensor, SensorSim
from greenbox.utils.catalog_client import get_device_config


class RaspberryHub:
    """
    Orchestrates independent sensor workers for a single Raspberry Pi zone.
    It receives its specific configuration upon initialization.
    """

    def __init__(self, raspberry_id: str, local_config: Dict[str, Any], is_sim: bool = True):
        self.raspberry_id = raspberry_id
        self.is_sim = is_sim
        
        # Sensor configuration is passed directly from the runner
        associated_sensors = local_config.get("sensors", [])

        # Get context (greenhouse, broker) from the central catalog
        device_context = get_device_config(self.raspberry_id)
        self.broker_ip = device_context["broker_ip"]
        self.broker_port = device_context["broker_port"]
        self.greenhouse_id = device_context["greenhouse_id"]
        
        logging.info(
            "[%s] Initializing. Context from catalog: [Greenhouse: %s, Broker: %s:%s]",
            self.raspberry_id, self.greenhouse_id, self.broker_ip, self.broker_port
        )

        # --- Initialize sensor workers ---
        self.topic = f"/{self.greenhouse_id}/{self.raspberry_id}/sensors/"

        cls = SensorSim if is_sim else Sensor

        self.sensors = [
            cls(s, self.broker_ip, self.broker_port, self.topic)
            for s in associated_sensors
        ]

        self._executor = None
        self.futures = []

    def start(self):
        """Start all sensor loops in parallel threads."""
        self._executor = ThreadPoolExecutor(max_workers=len(self.sensors))
        self.futures = [self._executor.submit(s.read_value) for s in self.sensors]
        logging.info(f"[{self.raspberry_id}] All %d sensor workers started.", len(self.sensors))

    def stop(self):
        """Signal graceful stop and wait for all workers to finish."""
        logging.info(f"[{self.raspberry_id}] Stopping all sensor workers...")
        for s in self.sensors:
            s.request_stop()
        
        # Wait for all threads to complete
        for f in self.futures:
            try:
                f.result(timeout=5) # Add a timeout to avoid blocking forever
            except Exception:
                logging.exception(f"[{self.raspberry_id}] Error in sensor worker during shutdown.")
        
        if self._executor:
            self._executor.shutdown(wait=True)
        logging.info(f"[{self.raspberry_id}] All sensor workers stopped.")

    def __str__(self):
        return pformat(self.__dict__, indent=1, sort_dicts=False)