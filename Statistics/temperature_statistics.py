import time
import json
import os
from influxdb_adaptor import InfluxDBAdaptor
from data_statistics import (
    moving_average, remove_outliers, calculate_variance_stddev, linear_trend,
    calculate_statistics
)
from tools.my_mqtt import MyMQTT


class MeasurementStatistics:
    def __init__(self, influxdb_adaptor, mqtt_client, base_topic):
        self.influxdb_adaptor = influxdb_adaptor
        self.mqtt_client = mqtt_client
        self.base_topic = base_topic  # Base topic for MQTT communication

    def publish_statistics(self, measurement_name, host_name, measurement_types):
        """
        Publishes statistics for specified measurement types (e.g., temperature, humidity).
        :param measurement_types: List of measurement types to process.
        """
        while True:
            for measurement_type in measurement_types:
                # Construct the full topic dynamically for this measurement type
                topic_name = f"{self.base_topic}"

                # Get measurement data from the adaptor
                json_data = self.influxdb_adaptor.get_json_data(
                    measurement_name, measurement_type, host_name, topic_name
                )
                data = json.loads(json_data)

                # Extract measurement values
                measurement_values = [entry['value'] for entry in data]

                if not measurement_values:
                    print(f"No {measurement_type} data available.")
                    continue  # Skip to next measurement type

                # Remove outliers
                cleaned_values = remove_outliers(measurement_values)

                # Calculate statistics
                variance, stddev = calculate_variance_stddev(cleaned_values)
                slope = linear_trend(cleaned_values)
                current_stats = calculate_statistics(cleaned_values)

                if current_stats:
                    # Prepare statistics for publication
                    timestamp = time.time()
                    stats_to_publish = {
                        "timestamp": timestamp,
                        f"mean_{measurement_type}": current_stats["mean"],
                        f"min_{measurement_type}": current_stats["min"],
                        f"max_{measurement_type}": current_stats["max"],
                        "variance": variance,
                        "stddev": stddev,
                        "slope_of_trend": slope
                    }

                    # Construct the statistics topic dynamically
                    stats_topic = f"{self.base_topic}/{measurement_type}/statistics"

                    # Publish statistics over MQTT
                    self.mqtt_client.myPublish(stats_topic, stats_to_publish)
                    print(f"[INFO] Published {measurement_type} statistics to {stats_topic}")

                    # Write statistics to InfluxDB
                    self.write_to_influxdb(stats_to_publish, topic_name)

            # Wait before republishing statistics
            time.sleep(60)

    def write_to_influxdb(self, stats, topic):
        """Write statistics to InfluxDB."""
        self.influxdb_adaptor.write_data(
            measurement_name="measurement_statistics",
            tags={
                "host": "MacBook-Pro-di-luca-3.local",
                "topic": topic  # Use the dynamic topic
            },
            fields={
                key: value for key, value in stats.items() if key != "timestamp"
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

    mqtt_client = MyMQTT(clientID="MeasurementStatsPublisher", broker="localhost", port=1883)
    mqtt_client.start()

    # Define identifiers for dynamic topic construction
    client_id = "01f20b9e-6df4-43df-9fd6-c1376bb2ba41"
    greenhouse_id = "greenhouse1"
    raspberry_id = "rb01"
    sensor_id = "dht11"

    # Construct the base topic dynamically
    base_topic = f"/{client_id}/{greenhouse_id}/{raspberry_id}/measurements/{sensor_id}"

    # Instantiate the MeasurementStatistics class
    measurement_statistics = MeasurementStatistics(
        influxdb_adaptor=influxdb_adaptor,
        mqtt_client=mqtt_client,
        base_topic=base_topic
    )

    # List of measurement types to process
    measurement_types = ["temperature", "humidity"]

    # Publish statistics for the measurement types
    try:
        measurement_statistics.publish_statistics(
            measurement_name="mqtt_consumer",
            host_name="MacBook-Pro-di-luca-3.local",
            measurement_types=measurement_types
        )
    except KeyboardInterrupt:
        print("Interruption received, stopping the statistics publisher.")
        mqtt_client.stop()
