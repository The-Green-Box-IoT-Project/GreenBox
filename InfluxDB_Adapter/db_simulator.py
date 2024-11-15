import pandas as pd
from datetime import timedelta

from utils.tools import (convert_str_to_datetime, read_env, mock_values_mapper, Today,
                         get_latest_entry_before_now, convert_df_to_list, extend_time_interval)
from utils.generate_mock_time_series import MockTimeSeriesWrapper


class InfluxDBSimulator(MockTimeSeriesWrapper):
    def __init__(self, values_file_path, measurement_name):
        super().__init__(values_file_path, measurement_name)
        self.timeseries = self.compose_timeseries()
        self.clock = Today()

    def query_timestamps(self, start_date='2024-01-01 00:00:00', end_date='2025-01-01 00:00:00'):
        """
        Queries and filters time series data within a specified time window.
        """
        # Extend the start and end times to include a broader range of data for resampling
        extended_start, extended_end = extend_time_interval(start_date, end_date)

        # Generate the time series data for the extended interval
        df = (
            self._generate_series(extended_start, extended_end)
            .resample('10s')  # Resample the data to 10-second intervals
            .interpolate(method='linear')  # Fill missing values with linear interpolation
            .round(2)  # Round values to 2 decimal places
        )

        # Convert the original start and end times to datetime objects
        exact_start, exact_end = convert_str_to_datetime(start_date, end_date)

        # Filter the DataFrame to only include rows within the exact time window
        df_filtered = df[(df.index >= exact_start) & (df.index <= exact_end)]

        # Debugging output: print the filtered data
        print(df_filtered)

        return df_filtered

    def query_last_minutes(self, minutes):
        # Generate the initial series
        df = self._generate_series(self.clock.start_day, self.clock.end_day)

        # Get the last entry and the following hour of data
        last_entry_index = get_latest_entry_before_now(df)
        curr_df = df.loc[last_entry_index:last_entry_index + timedelta(hours=1)]

        # Resample to 30-second intervals and interpolate
        df_resampled = curr_df.resample('10s').interpolate(method='linear').round(2)

        # Filter rows within the specified time window
        df_filtered = df_resampled[(df_resampled.index >= self.clock.last_minutes(minutes)) & (df_resampled.index <= self.clock.now)]
        print("Filtered Data:", df_filtered)

        return df_filtered

    def _generate_series(self, start, end):
        """Generates the time series data between the start and end timestamps."""
        index = self.create_time_index(start, end)
        series = {self.measurement_name: self.timeseries.generate(index)}
        df = self._adjust_values(pd.DataFrame(data=series, index=index))
        return df.apply(pd.to_numeric, errors='coerce')

    def _adjust_values(self, df):
        """Adjusts values based on the measurement type."""
        if self.measurement_name == "pH":
            df[self.measurement_name] = df[self.measurement_name].clip(lower=0, upper=12)
        elif self.measurement_name in ["soil_humidity", "humidity"]:
            df[self.measurement_name] = df[self.measurement_name].clip(lower=0, upper=100)
        elif self.measurement_name == "light":
            df[self.measurement_name] = df[self.measurement_name].clip(lower=0)
        return df


if __name__ == '__main__':
    # Load environment variables from the .env file
    read_env()

    # Specify the measurement type (e.g., humidity, pH, etc.)
    measurement_name = 'humidity'

    # Initialize the time series generator for the specified measurement
    timeseries_generator = InfluxDBSimulator(mock_values_mapper(measurement_name), measurement_name)

    # Query the last 5 minutes of data
    df = timeseries_generator.query_last_minutes(5)

    # Query data for a given time interval
    # df = timeseries_generator.query_timestamps('2024-11-01 15:35:00', '2024-11-01 15:55:00')

    # Convert the filtered DataFrame to a list of dictionaries, that contains the time (UNIX timestamp) and value
    print(convert_df_to_list(df))
