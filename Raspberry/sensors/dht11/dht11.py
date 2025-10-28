from pathlib import Path
from Raspberry.sensors.sensor import Sensor, SensorSim
from mockseries.mockseries import SimulateRealTimeReading

P = Path(__file__).parent.absolute()
CONFIG_FILE = P / 'config.json'


class DHT11(Sensor):
    """Real DHT11 sensor (temperature + humidity)."""
    def __init__(self, config_path=CONFIG_FILE, raspberry=None):
        super().__init__(config_path, raspberry)

    def read_value(self):
        # hardware_read must return {'temperature': ..., 'humidity': ...}
        self.loop(lambda: self.hardware_read(self.device_pin))


class DHT11_sim(SensorSim):
    """Simulated DHT11."""
    def __init__(self, config_path=CONFIG_FILE, raspberry=None):
        super().__init__(config_path, raspberry)

    @staticmethod
    def _fake_read():
        t = SimulateRealTimeReading('temperature').read()
        h = SimulateRealTimeReading('humidity').read()
        return {"temperature": float(t), "humidity": max(0.0, min(float(h), 100.0))}

    def read_value(self):
        self.loop(self._fake_read)  # i delta verranno applicati in SensorSim.send_value
