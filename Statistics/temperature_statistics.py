import time
import json
import os
from influxdb_adaptor import InfluxDBAdaptor
from data_statistics import (
    moving_average, remove_outliers, calculate_variance_stddev, linear_trend,
    calculate_statistics
)
from tools.my_mqtt import MyMQTT


class TemperatureStatistics:
    def __init__(self, influxdb_adaptor, mqtt_client, base_topic):
        self.influxdb_adaptor = influxdb_adaptor
        self.mqtt_client = mqtt_client
        self.base_topic = base_topic  # Base topic for MQTT communication

    def publish_statistics(self, measurement_name, field_name, host_name, topic_name):
        while True:
            # Get temperature data from the adaptor
            json_data = self.influxdb_adaptor.get_json_data(
                measurement_name, field_name, host_name, topic_name
            )
            data = json.loads(json_data)

            # Extract temperature values
            temperature_values = [entry['value'] for entry in data]

            if not temperature_values:
                print("No temperature data available.")
                time.sleep(60)
                continue  # Skip iteration if no data

            # Remove outliers
            cleaned_temperatures = remove_outliers(temperature_values)

            # Calculate statistics
            variance, stddev = calculate_variance_stddev(cleaned_temperatures)
            slope = linear_trend(cleaned_temperatures)
            current_stats = calculate_statistics(cleaned_temperatures)

            if current_stats:
                # Prepare statistics for publication
                timestamp = time.time()
                stats_to_publish = {
                    "timestamp": timestamp,
                    "mean_temperature": current_stats["mean"],
                    "min_temperature": current_stats["min"],
                    "max_temperature": current_stats["max"],
                    "variance": variance,
                    "stddev": stddev,
                    "slope_of_trend": slope
                }

                # **Construct the statistics topic dynamically**
                stats_topic = f"{self.base_topic}/statistics"

                # Publish statistics over MQTT
                self.mqtt_client.myPublish(stats_topic, stats_to_publish)

                # Write statistics to InfluxDB
                self.write_to_influxdb(stats_to_publish, topic_name)

            # Wait before republishing statistics
            time.sleep(60)

    def write_to_influxdb(self, stats, topic):
        """Write statistics to InfluxDB."""
        self.influxdb_adaptor.write_data(
            measurement_name="temperature_statistics",
            tags={
                "host": "MacBook-Pro-di-luca-3.local",
                "topic": topic  # Use the dynamic topic
            },
            fields={
                "mean_temperature": stats["mean_temperature"],
                "min_temperature": stats["min_temperature"],
                "max_temperature": stats["max_temperature"],
                "variance": stats["variance"],
                "stddev": stats["stddev"],
                "slope_of_trend": stats["slope_of_trend"]
            },
            timestamp=int(stats["timestamp"] * 1000)  # Timestamp in milliseconds
        )



if __name__ == "__main__":
    # Load environment variables from .env (optional)
    influxdb_adaptor = InfluxDBAdaptor(
        bucket=os.environ.get("INFLUXDB_BUCKET"),
        org=os.environ.get("INFLUXDB_ORG"),
        token=os.environ.get("INFLUX_TOKEN"),
        url=os.environ.get("INFLUXDB_URL")
    )

    mqtt_client = MyMQTT(clientID="TemperatureStatsPublisher", broker="localhost", port=1883)
    mqtt_client.start()

    # Define identifiers for dynamic topic construction
    client_id = "01f20b9e-6df4-43df-9fd6-c1376bb2ba41"
    greenhouse_id = "greenhouse1"
    raspberry_id = "rb01"
    sensor_id = "dht11"
    measurement_type = "temperature"

    # Construct the base topic dynamically
    base_topic = f"/{client_id}/{greenhouse_id}/{raspberry_id}/{sensor_id}/{measurement_type}"

    temperature_statistics = TemperatureStatistics(
        influxdb_adaptor=influxdb_adaptor,
        mqtt_client=mqtt_client,
        base_topic=base_topic
    )

    temperature_statistics.publish_statistics(
        measurement_name="mqtt_consumer",
        field_name="temperature",
        host_name="MacBook-Pro-di-luca-3.local",
        topic_name=base_topic
    )

