import os
import influxdb_client
import datetime
from dotenv import load_dotenv
import time
import json

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

    def query_last_five_minutes(self, measurement_name, field_name, host_name, topic_name):
        query = f'{self.query}\n  |> range(start: -5m)\n  |> filter(fn: (r) => r["_measurement"] == "{measurement_name}")\n  |> filter(fn: (r) => r["_field"] == "{field_name}")\n  |> filter(fn: (r) => r["host"] == "{host_name}")\n  |> filter(fn: (r) => r["topic"] == "{topic_name}")\n  |> aggregateWindow(every: 1m, fn: mean, createEmpty: false)\n  |> yield(name: "mean")'
        return query

    def execute_query(self, query):
        query_api = self.client.query_api()
        result = query_api.query(org=self.org, query=query)
        return result


def publish_values(influxdb, measurement_name, field_name, host_name, topic_name):
    while True:
        query = influxdb.query_last_five_minutes(measurement_name, field_name, host_name, topic_name)
        result = influxdb.execute_query(query)

        # Collect results
        values_to_publish = []
        for table in result:
            for record in table.records:
                values_to_publish.append({record.get_field(): record.get_value()})

        # Converti i dati in formato JSON
        json_data = json.dumps(values_to_publish)

        # Publish JSON data
        print("Publishing temperature:", json_data)
        # Implementa la logica per pubblicare i dati qui

        # Wait for 5 minutes before querying again
        time.sleep(300)


if __name__ == "__main__":
    # Creazione di un'istanza di InfluxDBReader
    influxdb = InfluxDBReader(bucket, org, token, url)

    # Definizione dei parametri per la query
    measurement_name = "mqtt_consumer"
    field_name = "temperature"
    host_name = "marzio-windows"
    topic_name = "sensor/data"

    publish_values(influxdb, measurement_name, field_name, host_name, topic_name)
