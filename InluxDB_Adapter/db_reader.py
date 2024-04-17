import os
import influxdb_client
import datetime
from dotenv import load_dotenv

load_dotenv()

token = os.environ.get("INFLUX_TOKEN")
bucket = os.getenv('INFLUXDB_BUCKET')
org = os.getenv('INFLUXDB_ORG')
url = os.getenv('INFLUXDB_URL')


class InfluxDBReader:

    def __init__(self, bucket, org, token, url):
        self.bucket = bucket
        self.org = org
        self.token = token
        self.url = url
        self.client = self.connect_client()
        self.query = self.query_instance()

    def connect_client(self):
        client = influxdb_client.InfluxDBClient(
            url=self.url,
            token=self.token,
            org=self.org
        )
        return client

    def query_instance(self):
        query = f'from(bucket:"{self.bucket}")'
        return query

    def query_range(self, minutes):
        self.query += f'\n  |> range(start: -{minutes}m)'

    def query_from_to_timestamp(self, start, end):
        start_time = start.strftime('%Y-%m-%dT%H:%M:%SZ')
        end_time = end.strftime('%Y-%m-%dT%H:%M:%SZ')
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
        result = query_api.query(org=self.org, query=self.query)
        return result


if __name__ == "__main__":
    # Creazione di un'istanza di InfluxDBReader
    influxdb = InfluxDBReader(bucket, org, token, url)

    # Definizione dei parametri per la query
    start_time = datetime.datetime(2024, 4, 16, 17, 27, 0)
    end_time = datetime.datetime(2024, 4, 16, 17, 36, 0)

    measurement_name = "mqtt_consumer"
    field_name = "temperature"
    host_name = "marzio-windows"
    topic_name = "sensor/data"
    window_period = "1m"
    yield_name = "mean"

    # Composizione della query finale
    # influxdb.query_from_to_timestamp(start_time, end_time)
    influxdb.query_range(5)
    influxdb.query_filter_measurement(measurement_name)
    influxdb.query_filter_field(field_name)
    influxdb.query_host_filter(host_name)
    influxdb.query_topic_filter(topic_name)
    influxdb.query_aggregate_window(window_period)
    influxdb.query_yield(yield_name)

    print(influxdb.query)

    # Esecuzione della query
    result = influxdb.execute_query()

    # Visualizzazione dei risultati
    print(result)

    for table in result:
        for record in table:
            print((record.get_field(), record.get_value()))


