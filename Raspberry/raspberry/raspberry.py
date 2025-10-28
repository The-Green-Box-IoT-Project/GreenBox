import os
from dotenv import load_dotenv
from concurrent.futures import ThreadPoolExecutor
from Raspberry.sensors.dht11.dht11 import DHT11, DHT11_sim
from Raspberry.sensors.PAR_meter.PAR_meter import PAR_meter, PAR_meter_sim
from Raspberry.sensors.pH_meter.pH_meter import pH_meter, pH_meter_sim
from Raspberry.sensors.soil_hygrometer.grodan import GrodanSens, GrodanSens_sim
from Raspberry.raspberry.connector import RaspberryConnector

load_dotenv()
greenbox_uuid = os.getenv('GREENBOX_UUID')


class RaspberryHub:
    """
    Orchestrates independent sensor workers.
    - Each sensor owns its MQTT client and publishes on its own.
    - Hub creates, starts, stops and supervises all sensors together.
    """

    def __init__(self, is_sim: bool = True):
        self.raspberry = RaspberryConnector()
        self.is_sim = is_sim

        # Choose real vs simulated sensors
        SensorDHT11 = DHT11_sim if is_sim else DHT11
        SensorPAR = PAR_meter_sim if is_sim else PAR_meter
        SensorPH = pH_meter_sim if is_sim else pH_meter
        SensorSoil = GrodanSens_sim if is_sim else GrodanSens

        # Build independent sensors (each one has its own MQTT client)
        self.sensors = [
            SensorDHT11(raspberry=self.raspberry),
            SensorPAR(raspberry=self.raspberry),
            SensorPH(raspberry=self.raspberry),
            SensorSoil(raspberry=self.raspberry),
        ]

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
