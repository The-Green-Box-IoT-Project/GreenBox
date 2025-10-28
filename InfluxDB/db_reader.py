import os
import influxdb_client
from dotenv import load_dotenv
from pprint import pprint
from datetime import datetime, timedelta

from utils.tools import convert_data_format

load_dotenv()

token = os.getenv("INFLUX_TOKEN")
bucket = os.getenv('INFLUXDB_BUCKET')
org = os.getenv('INFLUXDB_ORG')
url = os.getenv('INFLUXDB_URL')


class InfluxDBReader:
    # todo: valuta di spezzarla in due classi basso-alto livello (connection and query builder).
    def __init__(self, bucket, org, token, url):
        self.bucket = bucket
        self.org = org
        self.token = token
        self.url = url
        self.client = None
        self.query = None
        self._result = None

    def connect_client(self):
        self.client = influxdb_client.InfluxDBClient(
            url=self.url,
            token=self.token,
            org=self.org
        )

    def _query_instance(self):
        query = f'from(bucket:"{self.bucket}")'
        return query

    def _query_range(self, minutes):
        self.query += f'\n  |> range(start: -{minutes}m)'

    def _query_from_to_timestamp(self, start, end):

        # Adjust for the time difference between local time and UTC by subtracting one hour.
        # This ensures that the query matches the UTC-stored data in InfluxDB.
        start = start - timedelta(hours=1)
        end = end - timedelta(hours=1)

        # Convert the adjusted start and end times to ISO 8601 format with millisecond precision and a 'Z' suffix for UTC.
        start_time = start.isoformat(timespec='milliseconds') + 'Z'
        end_time = end.isoformat(timespec='milliseconds') + 'Z'

        # Append the range filter to the query, using the adjusted start and end times
        self.query += f'\n  |> range(start: {start_time}, stop: {end_time})'

    def _query_filter_measurement(self, measurement_name):
        self.query += f'\n  |> filter(fn: (r) => r["_measurement"] == "{measurement_name}")'

    def _query_filter_field(self, field_name):
        self.query += f'\n  |> filter(fn: (r) => r["_field"] == "{field_name}")'

    def _query_host_filter(self, host_name):
        self.query += f'\n  |> filter(fn: (r) => r["host"] == "{host_name}")'

    def _query_topic_filter(self, topic_name):
        self.query += f'\n  |> filter(fn: (r) => r["topic"] == "{topic_name}")'

    def _query_aggregate_window(self, window_period):
        self.query += f'\n  |> aggregateWindow(every: {window_period}, fn: mean, createEmpty: false)'

    def _query_yield(self, yield_name):
        self.query += f'\n  |> yield(name: "{yield_name}")'

    def execute_query(self):
        query_api = self.client.query_api()
        self._result = query_api.query(org=self.org, query=self.query)
        self.query = None

    def get_result(self):
        result = {}
        for table in self._result:
            for record in table:
                if record.get_field() not in result:
                    result[record.get_field()] = {}
                result[record.get_field()][record.get_time().isoformat()] = record.get_value()
        return result

    def query_last_minutes(
            self, minutes, measurement_name, field_name,
            host_name, topic_name, window_period, yield_name
    ):
        self.query = self._query_instance()
        self._query_range(minutes)
        self._query_filter_measurement(measurement_name)
        self._query_filter_field(field_name)
        self._query_host_filter(host_name)
        self._query_topic_filter(topic_name)
        self._query_aggregate_window(window_period)
        self._query_yield(yield_name)

    def query_timestamps(
            self, start_time, end_time, measurement_name, field_name,
            host_name, topic_name, window_period, yield_name
    ):
        self.query = self._query_instance()
        self._query_from_to_timestamp(start_time, end_time)
        self._query_filter_measurement(measurement_name)
        self._query_filter_field(field_name)
        self._query_host_filter(host_name)
        self._query_topic_filter(topic_name)
        self._query_aggregate_window(window_period)
        self._query_yield(yield_name)


if __name__ == "__main__":
    # Initialize an instance of InfluxDBReader with connection parameters
    influxdb = InfluxDBReader(bucket, org, token, url)

    # Define the time range for the query
    start_time = datetime(2024, 11, 15, 20, 30, 0)  # Start time in local time
    end_time = datetime(2024, 11, 15, 20, 39, 0)    # End time in local time
    last_minutes = 5  # Alternative query parameter for the last X minutes

    # Define additional query parameters in a dictionary for flexibility
    variables_dict = {
        "measurement_name": "mqtt_consumer",
        "field_name": "humidity",
        "host_name": "marzio-windows",
        "topic_name": "/01f20b9e-6df4-43df-9fd6-c1376bb2ba41/greenhouse1/rb01/measurements/dht11",
        "window_period": "1m",  # Aggregation period of 1 minute
        "yield_name": "mean"    # Name for the query yield
    }  # todo: questo deve essere compilato automaticamente in base all'utente

    # Connect to InfluxDB
    influxdb.connect_client()

    # Compose the query for the last X minutes or for a specific time range
    # Uncomment one of the following lines to choose which query to run:

    # Query for a specific time range using start and end times
    influxdb.query_timestamps(start_time, end_time, **variables_dict)

    # Query for the most recent data in the last specified minutes
    # influxdb.query_last_minutes(last_minutes, **variables_dict)
    print(influxdb.query)  # Print the generated query for debugging

    # Execute the query
    influxdb.execute_query()

    # Retrieve and print the results
    result = influxdb.get_result()
    pprint(result)

    # Convert the raw data format for easier consumption (e.g., for JSON output)
    formatted_result = convert_data_format(result)
    pprint(formatted_result)
