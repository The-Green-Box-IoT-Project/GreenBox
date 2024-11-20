import time
import json
import os
from Statistics.influxdb_adaptor import InfluxDBAdaptor
from Statistics.data_statistics import (
    moving_average, remove_outliers, calculate_variance_stddev, linear_trend,
    calculate_statistics)
from Statistics.tools.my_mqtt import MyMQTT


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
                    # Prepara le statistiche per la pubblicazione
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

                    # Costruisci il topic corretto per le statistiche
                    topic_parts = topic_name.split('/')
                    topic_parts[-2] = 'statistics'  # Sostituisci "measurements" con "statistics"
                    stats_topic = '/'.join(topic_parts) + f"/{measurement_type}"

                    # Pubblica le statistiche su MQTT
                    self.mqtt_client.myPublish(stats_topic, stats_to_publish)
                    print(f"[INFO] Published {measurement_type} statistics to {stats_topic}")

            # Wait before republishing statistics
            time.sleep(60)


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
            host_name="MBP-di-luca-3.lan",
            measurement_types=measurement_types
        )
    except KeyboardInterrupt:
        print("Interruption received, stopping the statistics publisher.")
        mqtt_client.stop()
