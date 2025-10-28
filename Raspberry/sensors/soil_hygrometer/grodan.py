from pathlib import Path
from Raspberry.sensors.sensor import Sensor, SensorSim
from mockseries.mockseries import SimulateRealTimeReading

P = Path(__file__).parent.absolute()
CONFIG_FILE = P / 'config.json'


class GrodanSens(Sensor):
    """Real Soil Humidity sensor."""

    def __init__(self, config_path=CONFIG_FILE, raspberry=None):
        super().__init__(config_path, raspberry)

    def read_value(self):
        """Continuously read from hardware and publish."""
        self.loop(lambda: self.hardware_read(self.device_pin))


class GrodanSens_sim(SensorSim):
    """Simulated Soil Humidity sensor for testing."""

    def __init__(self, config_path=CONFIG_FILE, raspberry=None):
        super().__init__(config_path, raspberry)

    @staticmethod
    def _fake_read():
        base_value = SimulateRealTimeReading('soil_humidity').read()
        return min(max(base_value, 0), 100)  # Ensures soil_humidity is between 0 and 100

    def read_value(self):
        """Continuously publish simulated pH readings."""
        self.loop(self._fake_read)
