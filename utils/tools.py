from datetime import datetime, timedelta
import pandas as pd
import os
import logging
from dotenv import load_dotenv


def extend_time_interval(start_time_str, end_time_str):
    """
    Extends a time interval given two timestamp strings.
    The start is rounded down to the previous hour, and the end is rounded up to the next hour.
    """
    # Convert strings to datetime objects
    start_time = datetime.strptime(start_time_str, "%Y-%m-%d %H:%M:%S")
    end_time = datetime.strptime(end_time_str, "%Y-%m-%d %H:%M:%S")

    # Round start time down to the previous hour
    extended_start = start_time.replace(minute=0, second=0, microsecond=0)

    # Round end time up to the next hour
    if end_time.minute != 0 or end_time.second != 0 or end_time.microsecond != 0:
        extended_end = (end_time + timedelta(hours=2)).replace(minute=0, second=0, microsecond=0)
    else:
        extended_end = end_time

    return extended_start, extended_end


def convert_df_to_list(df):
    """
    Converts a DataFrame with timestamps and values into a list of dictionaries
    with UNIX timestamps and rounded values.
    """
    result = [
        {
            "time": timestamp.timestamp(),  # Convert to UNIX timestamp
            "value": round(value, 2)  # Round value to two decimal places
        }
        for timestamp, value in df[df.columns[0]].items()
    ]
    return result


def convert_data_format(input_data):
    # List to hold the converted data in the desired format
    result = []

    # Extract the key and iterate over the timestamps and values
    for key, timestamps in input_data.items():
        for timestamp_str, value in timestamps.items():
            # Convert ISO8601 timestamp to UNIX timestamp (in seconds)
            timestamp = datetime.fromisoformat(timestamp_str.replace("Z", "+00:00")).timestamp()
            # Append the transformed data to the result list with rounded values
            result.append({
                "time": timestamp,
                "value": round(value, 2)  # Round to two decimal places
            })

    return result


def mock_values_mapper(measurement_name: str):
    if measurement_name in ['temperature', 'humidity']:
        sensor = 'dht11'
    elif measurement_name == 'light':
        sensor = 'PAR_meter'
    elif measurement_name == 'pH':
        sensor = 'pH_meter'
    elif measurement_name == 'soil_humidity':
        sensor = 'soil_hygrometer'
    else:
        raise ValueError(f'Unknown measurement_name - {measurement_name}. \nList of possible measurements: temperature, humidity, light, pH, soil_humidity.')
    return os.path.join(os.getenv('SENSORS'), sensor, 'mock_values.json')


class Today:
    def __init__(self):
        self.start_day = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        self.end_day = datetime.now().replace(hour=23, minute=59, second=59, microsecond=999999)
        self.now = datetime.now()

    def last_minutes(self, minutes: int):
        return self.now - timedelta(minutes=minutes)


def get_latest_entry_before_now(time_series: pd.Series):
    now = datetime.now()
    filtered_series = time_series[time_series.index < now]

    if not filtered_series.empty:
        latest_entry = filtered_series.index[-1]
        return latest_entry
    else:
        return None


def convert_str_to_datetime(start_date, end_date):
    if isinstance(start_date, str):
        start_date = datetime.strptime(start_date, "%Y-%m-%d %H:%M:%S")
    if isinstance(end_date, str):
        end_date = datetime.strptime(end_date, "%Y-%m-%d %H:%M:%S")
    return start_date, end_date


def read_env():
    load_dotenv()


def setup_logger():
    os.makedirs(os.getenv("LOGS"), exist_ok=True)
    logging.basicConfig(filename=os.path.join(os.getenv("LOGS"), f"{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}"),
                        level=logging.DEBUG,
                        format="%(asctime)s - %(levelname)s: %(message)s",
                        force=True)
