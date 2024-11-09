import json
import pandas as pd
from datetime import timedelta, datetime
from dotenv import load_dotenv
from mockseries.trend import LinearTrend
from mockseries.seasonality import YearlySeasonality, DailySeasonality
from mockseries.noise import RedNoise
from mockseries.utils import datetime_range

from utils.tools import get_latest_entry_before_now, convert_str_to_datetime, parse_dates


class SensorSimulator:
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
    def __init__(self, measure, start_date, end_date):
        self.start_date, self.end_date = start_date, end_date
        self.measure = measure
        self.ts_index = self._set_time_range()

    def _set_time_range(self):
        return datetime_range(
            granularity=timedelta(hours=1),
            start_time=self.start_date,
            end_time=self.end_date
        )

    def generate_trend(self):
        return LinearTrend(coefficient=0, time_unit=timedelta(days=1), flat_base=self.measure.base_value)

    def generate_daily_seasonality(self):
        return DailySeasonality(self.measure.daily_seasonality)

    def generate_yearly_seasonality(self):
        return YearlySeasonality(self.measure.yearly_seasonality)

    def generate_noise(self):
        return RedNoise(
            mean=self.measure.noise["mean"],
            std=self.measure.noise["std"],
            correlation=self.measure.noise["correlation"]
        )

    def generate_full_timeseries(self):
        # todo: remove this function. Each sensor has a customized time series shape. To be performed outside of this class
        return self.generate_trend() + self.generate_daily_seasonality() + self.generate_yearly_seasonality() + self.generate_noise()


class TimeSeriesGenerator:
    # todo: this class will simulate influxdb adapter
    def __init__(self, sensor: SensorSimulator, measurement, start_date: str = "2024-01-01", end_date: str = "2025-01-01"):
        # Convert start and end dates only if provided, else set to None
        self.start_date, self.end_date = (
            convert_str_to_datetime(start_date, end_date) if start_date and end_date else (None, None)
        )
        self.sensor = sensor
        self.measurement = [measurement] if isinstance(measurement, str) else measurement

    def generate_interval_time_series(self):
        all_series = {}
        for measure_name in self.measurement:
            measure = self.sensor.measures[measure_name]
            wrapper = MockTimeSeriesWrapper(measure, self.start_date, self.end_date)
            timeseries = wrapper.generate_full_timeseries()
            # fixme: don't use generate full timeseries (it's correct only for dht11 sensor)
            all_series[measure_name] = timeseries.generate(wrapper.ts_index)
        return pd.DataFrame(data=all_series, index=wrapper.ts_index)


class Today:
    # todo: change or move to sensor.py file (?)
    def __init__(self):
        self.start, self.end = parse_dates()


class SimulateRealTimeReading:
    # todo: move to sensor.py file
    def __init__(self, shape, index, measurement_name):
        self.shape = shape
        self.index = index
        self.measurement_name = measurement_name

    def read_last_measurement(self):
        # Generate today's time series and find the last measurement within the past hour
        series = {self.measurement_name: self.shape.generate(self.index)}
        df = pd.DataFrame(data=series, index=self.index)
        last_entry_index = get_latest_entry_before_now(df)
        curr_df = df.loc[last_entry_index:last_entry_index + timedelta(hours=1)].apply(pd.to_numeric, errors='coerce')

        # Resample to one-second intervals and interpolate with rounding
        df_resampled = curr_df.resample('1s').interpolate(method='linear').round(2)
        last_entry_index = get_latest_entry_before_now(df_resampled)
        return df_resampled.loc[last_entry_index][self.measurement_name]


if __name__ == "__main__":

    import matplotlib.pyplot as plt

    load_dotenv()
    sensor = SensorSimulator(r".\dht11\mock_values.json")
    dht11 = TimeSeriesGenerator(sensor, ["temperature"])
    dht11_value = dht11.generate_interval_time_series()
    print(dht11_value)

    # Grafico Lineare della Serie Temporale
    plt.figure(figsize=(12, 6))
    plt.plot(dht11_value.index[:], dht11_value[:])
    plt.title("Grafico Lineare della Serie Temporale (PAR)")
    plt.xlabel("Tempo")
    plt.ylabel("PAR")
    plt.show()
