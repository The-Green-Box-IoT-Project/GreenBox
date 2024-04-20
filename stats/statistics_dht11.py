import json
from stats.db_reader import *
import time
import statistics


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


def consume_published_values():
    while True:
        published_blocks = []

        influxdb = InfluxDBReader(bucket, org, token, url)

        measurement_name = "mqtt_consumer"
        field_name = "temperature"
        host_name = "MacBook-Pro-di-luca-2.local"
        topic_name = "sensor/data"

        query = influxdb.query_last_five_minutes(measurement_name, field_name, host_name, topic_name)
        result = influxdb.execute_query(query)

        values_in_block = []
        for table in result:
            for record in table.records:
                values_in_block.append(record.get_value())

        published_blocks.append(values_in_block)

        statistics_json = calculate_statistics(published_blocks)

        # Converti i dati in formato JSON
        json_data = json.dumps(statistics_json)

        # Stampa il JSON
        print("Statistics:", json_data)

        # Wait for 5 minutes before querying again
        time.sleep(300)


if __name__ == "__main__":
    consume_published_values()
