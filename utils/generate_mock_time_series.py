import json
import pandas as pd
from datetime import timedelta
from mockseries.trend import LinearTrend
from mockseries.seasonality import YearlySeasonality, DailySeasonality
from mockseries.noise import RedNoise
from mockseries.utils import datetime_range


class MockValuesReader:
    def __init__(self, mock_values_file_path: str) -> None:
        self.mock_values_file_path = mock_values_file_path
        self.load_values()

    def load_values(self):
        with open(self.mock_values_file_path, 'r') as f:
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
    """
    Composes a synthetic time series using trend, seasonality, and noise components.
    """

    def __init__(self, values_file_path, measurement_name):
        """
        Initializes the MockTimeSeriesWrapper with measurement data from a file.

        Args:
            values_file_path (str): Path to the file containing measurement values.
            measurement_name (str): The name of the measurement to retrieve.
        """
        self.measurement = MockValuesReader(values_file_path).measures[measurement_name]
        self.measurement_name = measurement_name

    @staticmethod
    def create_time_index(start_date=None, end_date=None):
        """
        Creates a time index for the series at hourly granularity.
        """
        return datetime_range(
            granularity=timedelta(hours=1),
            start_time=start_date,
            end_time=end_date
        )

    def trend_component(self):
        """Defines the linear trend component."""
        return LinearTrend(coefficient=0, time_unit=timedelta(days=1), flat_base=self.measurement.base_value)

    def daily_seasonality_component(self):
        """Defines the daily seasonality component."""
        return DailySeasonality(self.measurement.daily_seasonality)

    def yearly_seasonality_component(self):
        """Defines the yearly seasonality component."""
        return YearlySeasonality(self.measurement.yearly_seasonality)

    def noise_component(self):
        """Defines the noise component."""
        return RedNoise(
            mean=self.measurement.noise["mean"],
            std=self.measurement.noise["std"],
            correlation=self.measurement.noise["correlation"]
        )

    def compose_timeseries(self):
        """
        Combines trend, seasonality, and noise components to create the full time series.

        Returns:
            pd.Series: The composed time series.
        """
        trend = self.trend_component()
        daily_seasonality = self.daily_seasonality_component()
        yearly_seasonality = self.yearly_seasonality_component()
        noise = self.noise_component()

        if self.measurement_name == 'light':
            # Light measurement combines daily and yearly seasonality multiplication
            return trend + daily_seasonality * yearly_seasonality + noise
        else:
            return trend + daily_seasonality + yearly_seasonality + noise
