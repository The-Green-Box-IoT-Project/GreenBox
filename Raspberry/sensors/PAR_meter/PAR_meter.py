from pathlib import Path
from Raspberry.sensors.sensor import SensorSim
from mockseries.mockseries import SimulateRealTimeReading

P = Path(__file__).parent.absolute()
CONFIG_FILE = P / 'config.json'


class PAR_meter(SensorSim):
    """Real PAR sensor with dual outputs: natural and internal."""
    def __init__(self, config_path=CONFIG_FILE, raspberry=None):
        super().__init__(config_path, raspberry)

    def _read_both(self):
        """Read hardware once, expose both natural and internal slots.
        'light' will receive actuator deltas, 'light_natural' stays raw.
        """
        v = float(self.hardware_read(self.device_pin))
        v = max(v, 0.0)
        return {"light": v, "light_natural": v}

    def read_value(self):
        """Continuously read from hardware and publish both values."""
        self.loop(self._read_both)


class PAR_meter_sim(SensorSim):
    """Simulated PAR sensor for testing, dual outputs."""
    def __init__(self, config_path=CONFIG_FILE, raspberry=None):
        super().__init__(config_path, raspberry)

    @staticmethod
    def _fake_read():
        base_value = SimulateRealTimeReading('light').read()
        v = max(float(base_value), 0.0)
        # 'light' will be adjusted by SensorSim, 'light_natural' remains base
        return {"light": v, "light_natural": v}

    def read_value(self):
        """Continuously publish simulated light readings (both values)."""
        self.loop(self._fake_read)
