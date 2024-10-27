import json
import time
import pandas as pd
from datetime import timedelta, datetime
from dotenv import load_dotenv
from mockseries.trend import LinearTrend
from mockseries.seasonality import YearlySeasonality, DailySeasonality
from mockseries.noise import RedNoise
from mockseries.utils import datetime_range

from Raspberry_Connector.tools import get_latest_entry_before_now, convert_str_to_datetime


class Sensor:
    def __init__(self, sensor_file: str) -> None:
        self.sensor_file = sensor_file
        self.load_info()

    def load_info(self):
        with open(self.sensor_file, 'r') as f:
            data = json.load(f)
        # Generalize to support multiple measures (e.g., temperature, humidity)
        self.measures = {k: self.Measure(v) for k, v in data.items()}

    class Measure:
        def __init__(self, attributes: dict) -> None:
            self.base_value = attributes["base_value"]
            # Initialize seasonality with a single function
            self.daily_seasonality = self._compute_seasonality(attributes.get("daily_seasonality"), "hours")
            self.yearly_seasonality = self._compute_seasonality(attributes.get("yearly_seasonality"), "days")
            self.noise = attributes.get("noise", {"mean": 0, "std": 0.5, "correlation": 0.5})

        @staticmethod
        def _compute_seasonality(times_value: dict, time_unit: str):
            if not times_value:
                return {}
            timedelta_dict = {timedelta(**{time_unit: unit}): value for unit, value in
                              zip(times_value["times"], times_value["values"])}
            return timedelta_dict


class MockTimeSeriesWrapper:
    def __init__(self, measure: Sensor.Measure, start_date: datetime, end_date: datetime):
        self.start_date, self.end_date = start_date, end_date
        self.measure = measure
        self.ts_index = self.set_time_range()

    def set_time_range(self):
        return datetime_range(
            granularity=timedelta(hours=1),
            start_time=self.start_date,
            end_time=self.end_date
        )

    def generate_full_timeseries(self):
        # Create and sum all components of the time series
        trend = LinearTrend(coefficient=0, time_unit=timedelta(days=1), flat_base=self.measure.base_value)
        daily_seasonality = DailySeasonality(self.measure.daily_seasonality)
        yearly_seasonality = YearlySeasonality(self.measure.yearly_seasonality)
        noise = RedNoise(
            mean=self.measure.noise["mean"],
            std=self.measure.noise["std"],
            correlation=self.measure.noise["correlation"]
        )
        return trend + daily_seasonality + yearly_seasonality + noise


class TimeSeriesGenerator:
    def __init__(self, sensor: Sensor, measurement, start_date: str = "2024-01-01", end_date: str = "2025-01-01"):
        # Convert start and end dates only if provided, else set to None
        self.start_date, self.end_date = (
            convert_str_to_datetime(start_date, end_date) if start_date and end_date else (None, None)
        )
        self.sensor = sensor
        self.measurement = [measurement] if isinstance(measurement, str) else measurement

    def _generate_time_series(self, start_date=None, end_date=None):
        # Use provided dates or default to today's date range
        if start_date is None or end_date is None:
            start_date = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
            end_date = start_date + timedelta(days=1)

        all_series = {}
        for measure_name in self.measurement:
            measure = self.sensor.measures[measure_name]
            wrapper = MockTimeSeriesWrapper(measure, start_date, end_date)
            timeseries = wrapper.generate_full_timeseries()
            all_series[measure_name] = timeseries.generate(wrapper.ts_index)
        return pd.DataFrame(data=all_series, index=wrapper.ts_index)

    def _generate_current_time_series(self):
        # Calls generate_time_series with today’s date
        return self._generate_time_series()

    def generate_interval_time_series(self):
        # Calls generate_time_series with initialized start and end dates
        return self._generate_time_series(self.start_date, self.end_date)

    def read_last_measurement(self):
        # Generate today's time series and find the last measurement within the past hour
        df = self._generate_current_time_series()
        last_entry_index = get_latest_entry_before_now(df)
        curr_df = df.loc[last_entry_index:last_entry_index + timedelta(hours=1)].apply(pd.to_numeric, errors='coerce')

        # Resample to one-second intervals and interpolate with rounding
        df_resampled = curr_df.resample('1s').interpolate(method='linear').round(2)
        last_entry_index = get_latest_entry_before_now(df_resampled)
        return df_resampled.loc[last_entry_index]


if __name__ == "__main__":
    t0 = time.time()
    load_dotenv()
    sensor = Sensor(r".\dht11\mock_values.json")
    dht11 = TimeSeriesGenerator(sensor, ["temperature", "humidity"])
    print(dht11.generate_interval_time_series())
    print(time.time()-t0)
