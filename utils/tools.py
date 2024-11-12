from datetime import datetime
import pandas as pd
import os
import logging
from dotenv import load_dotenv


class Today:
    def __init__(self):
        self.start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        self.end = datetime.now().replace(hour=23, minute=59, second=59, microsecond=999999)


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
        start_date = datetime.strptime(start_date, "%Y-%m-%d")
    if isinstance(end_date, str):
        end_date = datetime.strptime(end_date, "%Y-%m-%d")
    return start_date, end_date


def read_env():
    load_dotenv()


def setup_logger():
    os.makedirs(os.getenv("LOGS"), exist_ok=True)
    logging.basicConfig(filename=os.path.join(os.getenv("LOGS"), f"{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}"),
                        level=logging.DEBUG,
                        format="%(asctime)s - %(levelname)s: %(message)s",
                        force=True)
