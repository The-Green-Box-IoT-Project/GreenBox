import pandas as pd
from datetime import timedelta
from utils.tools import (
    convert_str_to_datetime, read_env, Today,
    convert_df_to_list, convert_list_to_df, extend_time_interval
)
from mockseries.mockseries import Measure, datetime_range


class InfluxDBSimulator:
    """Generate mock series and query time windows in a Pandas-like way."""
    def __init__(self, measurement_name: str):
        self.measurement_name = measurement_name
        self.measure = Measure.from_json(measurement_name)
        self.clock = Today()

    def query_timestamps(self, start_date='2025-01-01 00:00:00', end_date='2025-12-01 00:00:00'):
        """Return records within [start_date, end_date] at ~10s resolution."""
        extended_start, extended_end = extend_time_interval(start_date, end_date)
        df = (
            self._generate_series(extended_start, extended_end)
            .resample('10s')
            .interpolate('linear')
            .round(2)
        )
        exact_start, exact_end = convert_str_to_datetime(start_date, end_date)
        df_filtered = df[(df.index >= exact_start) & (df.index <= exact_end)]
        data = convert_df_to_list(df_filtered)
        for d in data:
            if "value" in d:
                d[self.measurement_name] = d.pop("value")
        return data

    def query_last_minutes(self, minutes: int):
        """Return the last <minutes> of data at ~10s resolution."""
        end_ts = self.clock.now
        start_ts = self.clock.last_minutes(minutes)
        start_gen = start_ts.replace(hour=0, minute=0, second=0, microsecond=0)
        end_gen = end_ts.replace(hour=23, minute=59, second=59, microsecond=999999)
        df = self._generate_series(start_gen, end_gen)
        df_10s = df.resample('10s').interpolate('linear').round(2)
        df_filtered = df_10s[(df_10s.index >= start_ts) & (df_10s.index <= end_ts)]
        data = convert_df_to_list(df_filtered)
        for d in data:
            if "value" in d:
                d[self.measurement_name] = d.pop("value")
        return data

    def query_last_value(self, at_time=None):
        """Return the last available record ≤ at_time (or now)."""
        ref_ts = convert_str_to_datetime(at_time, at_time)[0] if isinstance(at_time, str) else (at_time or self.clock.now)
        start_gen = ref_ts.replace(hour=0, minute=0, second=0, microsecond=0)
        end_gen = ref_ts.replace(hour=23, minute=59, second=59, microsecond=999999)
        df = self._generate_series(start_gen, end_gen)
        df_10s = df.resample('10s').interpolate('linear').round(2)
        if df_10s.index[0] > ref_ts:
            return None
        last_row = df_10s.loc[:ref_ts].tail(1)
        data = convert_df_to_list(last_row)
        if not data:
            return None
        if "value" in data[0]:
            data[0][self.measurement_name] = data[0].pop("value")
        return data[0]

    def _generate_series(self, start, end) -> pd.DataFrame:
        """Generate hourly series in [start, end) and return a DataFrame."""
        index = datetime_range(timedelta(hours=1), start, end)
        s = self.measure.generate(self.measurement_name, index).rename(self.measurement_name)
        df = self._adjust_values(s.to_frame())
        return df.apply(pd.to_numeric, errors='coerce')

    def _adjust_values(self, df: pd.DataFrame) -> pd.DataFrame:
        """Clip values by measurement semantics."""
        name = self.measurement_name
        if name == "pH":
            df[name] = df[name].clip(lower=0, upper=12)
        elif name in ["soil_humidity", "humidity"]:
            df[name] = df[name].clip(lower=0, upper=100)
        elif name == "light":
            df[name] = df[name].clip(lower=0)
        return df


if __name__ == '__main__':
    read_env()
    measurement_name = 'soil_humidity'
    sim = InfluxDBSimulator(measurement_name)
    measurements = sim.query_last_minutes(3600)
    # measurements = sim.query_timestamps('2025-03-01 15:35:00', '2025-03-01 15:55:00')
    print(convert_list_to_df(measurements))
