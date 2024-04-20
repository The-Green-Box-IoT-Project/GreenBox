import os
import influxdb_client
import datetime
from dotenv import load_dotenv

load_dotenv()

token = os.getenv("INFLUX_TOKEN")
bucket = os.getenv('INFLUXDB_BUCKET')
org = os.getenv('INFLUXDB_ORG')
url = os.getenv('INFLUXDB_URL')


class InfluxDBReader:
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

    def query_instance(self):
        query = f'from(bucket:"{self.bucket}")'
        return query

    def query_range(self, minutes):
        self.query += f'\n  |> range(start: -{minutes}m)'

    def query_from_to_timestamp(self, start, end):
        start_time = start.isoformat() + 'Z'
        end_time = end.isoformat() + 'Z'
        self.query += f'\n  |> range(start: {start_time}, stop: {end_time})'

    def query_filter_measurement(self, measurement_name):
        self.query += f'\n  |> filter(fn: (r) => r["_measurement"] == "{measurement_name}")'

    def query_filter_field(self, field_name):
        self.query += f'\n  |> filter(fn: (r) => r["_field"] == "{field_name}")'

    def query_host_filter(self, host_name):
        self.query += f'\n  |> filter(fn: (r) => r["host"] == "{host_name}")'

    def query_topic_filter(self, topic_name):
        self.query += f'\n  |> filter(fn: (r) => r["topic"] == "{topic_name}")'

    def query_aggregate_window(self, window_period):
        self.query += f'\n  |> aggregateWindow(every: {window_period}, fn: mean, createEmpty: false)'

    def query_yield(self, yield_name):
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

    def compose_query_last_minutes(
            self, minutes, measurement_name, field_name,
            host_name, topic_name, window_period, yield_name
    ):
        self.query = self.query_instance()
        self.query_range(minutes)
        self.query_filter_measurement(measurement_name)
        self.query_filter_field(field_name)
        self.query_host_filter(host_name)
        self.query_topic_filter(topic_name)
        self.query_aggregate_window(window_period)
        self.query_yield(yield_name)

    def compose_query_timestamps(
            self, start_time, end_time, measurement_name, field_name,
            host_name, topic_name, window_period, yield_name
    ):
        self.query = self.query_instance()
        self.query_from_to_timestamp(start_time, end_time)
        self.query_filter_measurement(measurement_name)
        self.query_filter_field(field_name)
        self.query_host_filter(host_name)
        self.query_topic_filter(topic_name)
        self.query_aggregate_window(window_period)
        self.query_yield(yield_name)


if __name__ == "__main__":
    # Creazione di un'istanza di InfluxDBReader
    influxdb = InfluxDBReader(bucket, org, token, url)

    # Definizione dei parametri per la query
    start_time = datetime.datetime(2024, 4, 16, 17, 27, 0)
    end_time = datetime.datetime(2024, 4, 24, 17, 36, 0)
    last_minutes = 5

    variables_dict = {
        "measurement_name": "mqtt_consumer",
        "field_name": "temperature",
        "host_name": "SteurendoPPC",
        "topic_name": "sensor/data",
        "window_period": "1m",
        "yield_name": "mean"
    }

    # Composizione della query finale
    influxdb.compose_query_timestamps(start_time, end_time, **variables_dict)
    # influxdb.compose_query_last_minutes(last_minutes, **variables_dict)
    print(influxdb.query)

    # Esecuzione della query
    influxdb.execute_query()
    result = influxdb.get_result()
    print(result)
