import os
import sys
import influxdb_client
from influxdb_client.client.write_api import SYNCHRONOUS

bucket = "DHT11"
org = "GreenBox"
token = os.environ.get("INFLUX_TOKEN")

# Store the URL of your InfluxDB instance
url = "http://localhost:8086"

client = influxdb_client.InfluxDBClient(
    url=url,
    token=token,
    org=org
)

# Query script
query_api = client.query_api()
query = 'from(bucket:"DHT11")\
|> range(start: -90m)\
|> filter(fn:(r) => r._measurement == "mqtt_consumer")\
|> filter(fn:(r) => r._field == "temperature")'
result = query_api.query(org=org, query=query)
results = []
for table in result:
    for record in table.records:
        results.append((record.get_field(), record.get_value()))

print(results)
