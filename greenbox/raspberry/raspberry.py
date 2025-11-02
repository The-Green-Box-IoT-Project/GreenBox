from pprint import pformat
from concurrent.futures import ThreadPoolExecutor

from greenbox.raspberry.sensors import Sensor, SensorSim
from greenbox.utils.catalog_client import log_to_catalog


class RaspberryHub:
    """
    Orchestrates independent sensor workers.
    - Each sensor owns its MQTT client and publishes on its own.
    - Hub creates, starts, stops and supervises all sensors together.
    """

    def __init__(self, is_sim: bool = True):

        # Simulation?
        self.is_sim = is_sim

        # GET from catalog
        cfg = log_to_catalog()
        self.broker_ip = cfg["broker_ip"]
        self.broker_port = cfg["broker_port"]
        self.greenhouse_id = cfg["greenhouse_id"]
        self.raspberry_id = cfg["raspberry_id"]
        associated_sensors = cfg["sensors"]

        self.time_interval = 5  # seconds
        self.topic = f"""/{self.greenhouse_id}/{self.raspberry_id}/sensors/"""

        # Choose real vs simulated sensors
        cls = SensorSim if is_sim else Sensor

        # Build independent sensors (each one has its own MQTT client)
        self.sensors = [cls(s, self.broker_ip, self.broker_port, self.topic, self.time_interval) for s in associated_sensors]

        self._executor = None
        self.futures = []

    def start(self):
        """Start all sensor loops in parallel threads."""
        self._executor = ThreadPoolExecutor(max_workers=len(self.sensors))
        self.futures = [self._executor.submit(s.read_value) for s in self.sensors]

    def stop(self):
        """Signal graceful stop and wait for all workers to finish."""
        for s in self.sensors:
            # Each sensor implements request_stop() checked inside its loop
            s.request_stop()
        for f in self.futures:
            try:
                f.result()
            except Exception:
                # Keep shutdown resilient: one failed worker must not block others
                pass
        if self._executor:
            self._executor.shutdown(wait=True)

    def __str__(self):
        return pformat(self.__dict__, indent=1, sort_dicts=False)
