from datetime import datetime
import pandas as pd


def get_latest_entry_before_now(time_series: pd.Series):
    now = datetime.now()
    filtered_series = time_series[time_series.index < now]

    if not filtered_series.empty:
        latest_entry = filtered_series.index[-1]
        return latest_entry
    else:
        return None
