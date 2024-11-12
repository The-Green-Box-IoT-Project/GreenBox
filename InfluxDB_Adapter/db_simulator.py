import pandas as pd
import os

from utils.tools import convert_str_to_datetime, read_env
from utils.generate_mock_time_series import MockTimeSeriesWrapper


class TimeSeriesGenerator(MockTimeSeriesWrapper):
    def __init__(self, measurement_name, values_file_path, start_date='2024-01-01', end_date='2025-01-01'):
        super().__init__(measurement_name, values_file_path)
        self.start, self.end = (
            convert_str_to_datetime(start_date, end_date) if start_date and end_date else (None, None)
        )
        self.index = self.create_time_index(self.start, self.end)
        self.timeseries = self.compose_timeseries()

    def generate_interval_time_series(self):
        series = {self.measurement_name: self.timeseries.generate(self.index)}
        df = pd.DataFrame(data=series, index=self.index)
        return df


if __name__ == '__main__':
    read_env()
    mock_values = os.path.join(os.getenv('SENSORS'), 'dht11', 'mock_values.json')
    measurement_name = 'temperature'
    timeseries_generator = TimeSeriesGenerator(mock_values, measurement_name, start_date='2024-09-01', end_date='2025-11-10')
    df = timeseries_generator.generate_interval_time_series()
    print(df)
