import os
import influxdb_client
import json
from dotenv import load_dotenv

# Carica le variabili d'ambiente dal file .env
load_dotenv()

token = os.getenv("INFLUX_TOKEN")
bucket = os.getenv('INFLUXDB_BUCKET')
org = os.getenv('INFLUXDB_ORG')
url = os.getenv('INFLUXDB_URL')


class InfluxDBAdaptor:
    def __init__(self, bucket, org, token, url):
        self.bucket = bucket
        self.org = org
        self.token = token
        self.url = url
        self.client = self.connect_client()

    def connect_client(self):
        # Connessione a InfluxDB
        client = influxdb_client.InfluxDBClient(
            url=self.url,
            token=self.token,
            org=self.org
        )
        return client

    def query_data(self, measurement_name, field_name, host_name, topic_name, time_range="-5m"):
        # Query per leggere i dati da InfluxDB negli ultimi 'time_range'
        query = f'''
        from(bucket:"{self.bucket}")
        |> range(start: {time_range})
        |> filter(fn: (r) => r["_measurement"] == "{measurement_name}")
        |> filter(fn: (r) => r["_field"] == "{field_name}")
        |> filter(fn: (r) => r["host"] == "{host_name}")
        |> filter(fn: (r) => r["topic"] == "{topic_name}")
        '''
        query_api = self.client.query_api()
        result = query_api.query(org=self.org, query=query)
        return result

    def get_json_data(self, measurement_name, field_name, host_name, topic_name, time_range="-5m"):
        # Ottieni i dati e li converte in JSON
        result = self.query_data(measurement_name, field_name, host_name, topic_name, time_range)
        values_to_publish = []

        for table in result:
            for record in table.records:
                # Converte il tempo in timestamp UNIX (secondi con millisecondi)
                data = {
                    "time": record.get_time().timestamp(),  # Ottiene il timestamp UNIX
                    "value": record.get_value()
                }
                values_to_publish.append(data)

        # Converti i dati in JSON
        json_data = json.dumps(values_to_publish)
        return json_data
