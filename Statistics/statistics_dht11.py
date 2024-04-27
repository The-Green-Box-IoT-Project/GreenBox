import time
import json
import statistics
from Statistics.db_reader import *
from Raspberry_Connector.tools.my_mqtt import MyMQTT


def calculate_statistics(blocks):
    stats_list = []
    for block in blocks:
        if block:
            mean_value = statistics.mean(block)
            variance_value = statistics.variance(block)
            max_value = max(block)
            min_value = min(block)
            count_below_20 = sum(1 for value in block if value < 20)
            stats_list.append({
                "temperature_mean": mean_value,
                "temperature_variance": variance_value,
                "max_value": max_value,
                "min_value": min_value,
                "count_below_20": count_below_20
            })
    return stats_list


def consume_published_values(mqtt_client, topic):
    while True:
        influxdb = InfluxDBReader(bucket, org, token, url)
        measurement_name = "mqtt_consumer"
        field_name = "temperature"
        host_name = "marzio-windows"
        topic_name = "sensor/data"

        query = influxdb.query_last_five_minutes(measurement_name, field_name, host_name, topic_name)
        result = influxdb.execute_query(query)

        values_in_block = []
        for table in result:
            for record in table.records:
                values_in_block.append(record.get_value())

        statistics_json = calculate_statistics([values_in_block])

        # Pubblica le statistiche su MQTT
        mqtt_client.myPublish(topic, statistics_json)

        # Stampa le statistiche in console ogni 60 secondi
        print("Published Statistics:", json.dumps(statistics_json, indent=4))

        # Attendi 60 secondi prima di ripetere la query e la pubblicazione
        time.sleep(60)


if __name__ == "__main__":
    clientID = "MyMQTTClient"
    broker_address = "localhost"  # Cambia con l'indirizzo del tuo broker MQTT
    broker_port = 1883
    mqtt_client = MyMQTT(clientID, broker_address, broker_port)
    mqtt_client.start()

    try:
        topic = "statistics"
        consume_published_values(mqtt_client, topic)
    finally:
        mqtt_client.stop()