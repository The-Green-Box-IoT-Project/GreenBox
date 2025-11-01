import pandas as pd
from datetime import timedelta
import os
import sys

sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from utils.tools import (convert_str_to_datetime, read_env, mock_values_mapper, Today,
                         get_latest_entry_before_now, convert_df_to_list, extend_time_interval)
from utils.generate_mock_time_series import MockTimeSeriesWrapper


class InfluxDBSimulator(MockTimeSeriesWrapper):
    def __init__(self, values_file_path, measurement_name):
        super().__init__(values_file_path, measurement_name)
        self.timeseries = self.compose_timeseries()
        self.clock = Today()

    def query_timestamps(self, start_date='2025-01-01 00:00:00', end_date='2025-12-01 00:00:00'):
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

        data = convert_df_to_list(df_filtered)

        # Modifica ogni record sostituendo la chiave "value" con il nome della misurazione (es. "temperature")
        for d in data:
            if "value" in d:
                d[self.measurement_name] = d.pop("value")

        return data

    def query_last_minutes(self, minutes: int):
        # Calcola finestra esatta
        end_ts = self.clock.now
        start_ts = self.clock.last_minutes(minutes)

        # Per essere sicuri di coprire anche ieri, generiamo dal giorno di start_ts al fine giornata di end_ts
        start_gen = start_ts.replace(hour=0, minute=0, second=0, microsecond=0)
        end_gen = end_ts.replace(hour=23, minute=59, second=59, microsecond=999999)

        # Genera serie "grezza" sull'intervallo esteso (indice orario)
        df = self._generate_series(start_gen, end_gen)

        # Resample a 10s e interpolazione
        df_10s = df.resample('10s').interpolate(method='linear').round(2)

        # Filtro esatto della finestra richiesta
        df_filtered = df_10s[(df_10s.index >= start_ts) & (df_10s.index <= end_ts)]

        data = convert_df_to_list(df_filtered)

        # Rinomina la chiave "value" con il nome della misura
        for d in data:
            if "value" in d:
                d[self.measurement_name] = d.pop("value")

        return data

    def query_last_value(self, at_time=None):
        """
        Restituisce l'ultimo dato disponibile (<= at_time se fornito, altrimenti 'now').

        Ritorna un dict del tipo:
        {
            "timestamp": "...",
            "<measurement_name>": <valore_float>
        }
        oppure None se non ci sono dati.
        """
        # Tempo di riferimento: ora del clock o uno specificato
        ref_ts = convert_str_to_datetime(at_time, at_time)[0] if isinstance(at_time, str) else (at_time or self.clock.now)

        # Generiamo una finestra "sicura" per coprire la giornata del ref_ts
        start_gen = ref_ts.replace(hour=0, minute=0, second=0, microsecond=0)
        end_gen = ref_ts.replace(hour=23, minute=59, second=59, microsecond=999999)

        # Serie grezza → resample a 10s → interpolazione
        df = self._generate_series(start_gen, end_gen)
        df_10s = df.resample('10s').interpolate(method='linear').round(2)

        # Prendiamo l'ultimo campione disponibile <= ref_ts
        if df_10s.index[0] > ref_ts:
            return None  # nessun dato fino a ref_ts

        last_row = df_10s.loc[:ref_ts].tail(1)

        # Convertiamo in lista di dict e rinominiamo "value" come negli altri metodi
        data = convert_df_to_list(last_row)
        if not data:
            return None

        # Uniformiamo la chiave come negli altri metodi (in caso convert_df_to_list usi "value")
        if "value" in data[0]:
            data[0][self.measurement_name] = data[0].pop("value")

        return data[0]

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
    measurement_name = 'soil_humidity'

    # Initialize the time series generator for the specified measurement
    timeseries_generator = InfluxDBSimulator(mock_values_mapper(measurement_name), measurement_name)

    # Query the last 5 minutes of data
    measurements = timeseries_generator.query_last_minutes(3600)

    # Query data for a given time interval
    #measurements = timeseries_generator.query_timestamps('2025-03-01 15:35:00', '2025-03-01 15:55:00')
    # print(type(measurements))

    print(measurements)
