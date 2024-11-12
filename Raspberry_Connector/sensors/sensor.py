import pandas as pd
import json
from pathlib import Path
from datetime import timedelta

from utils.tools import get_latest_entry_before_now, Today
from utils.generate_mock_time_series import MockTimeSeriesWrapper

P = Path(__file__).parent.absolute()
CONFIG_FILE = P / 'config.json'


def load_sensor_attributes(device_config):
    with open(device_config, 'r') as f:
        data = json.load(f)
        device_id = data['device_id']
        device_name = data['device_name']
        device_pin = data['pin']
        device_measurements = data['measurements']
    return device_id, device_name, device_pin, device_measurements


def hardware_read(pin):
    raise NotImplementedError


class Sensor:
    def __init__(self, config_path):
        (self.device_id,
         self.device_name,
         self.device_pin,
         self.measurements) = load_sensor_attributes(config_path)

    def _build_topics(self, parent_topic):
        return parent_topic + '/measurements/' + self.device_id


class SimulateRealTimeReading(MockTimeSeriesWrapper):
    def __init__(self, values_file_path, measurement_name):
        super().__init__(values_file_path, measurement_name)
        self.index = self.create_time_index(Today().start, Today().end)
        self.timeseries = self.compose_timeseries()

    def read(self):
        # Generate today's time series and find the last measurement within the past hour
        series = {self.measurement_name: self.timeseries.generate(self.index)}
        df = pd.DataFrame(data=series, index=self.index)
        last_entry_index = get_latest_entry_before_now(df)
        curr_df = df.loc[last_entry_index:last_entry_index + timedelta(hours=1)].apply(pd.to_numeric, errors='coerce')

        # Resample to one-second intervals and interpolate with rounding
        df_resampled = curr_df.resample('1s').interpolate(method='linear').round(2)
        last_entry_index = get_latest_entry_before_now(df_resampled)
        return df_resampled.loc[last_entry_index][self.measurement_name]
