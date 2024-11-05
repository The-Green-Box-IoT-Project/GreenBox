import time
import json
import os  # Per accedere alle variabili di ambiente
from influxdb_adaptor import InfluxDBAdaptor
from data_statistics import (
    moving_average, remove_outliers, calculate_variance_stddev, linear_trend,
    calculate_statistics
)
from tools.my_mqtt import MyMQTT


class TemperatureStatistics:
    def __init__(self, influxdb_adaptor, mqtt_client):
        self.influxdb_adaptor = influxdb_adaptor
        self.mqtt_client = mqtt_client  # Istanza del client MQTT

    def publish_statistics(self, measurement_name, field_name, host_name, topic_name):
        while True:
            # Ottieni i dati della temperatura dall'adaptor
            json_data = self.influxdb_adaptor.get_json_data(
                measurement_name, field_name, host_name, topic_name
            )
            data = json.loads(json_data)

            # Estrai i valori di temperatura
            temperature_values = [entry['value'] for entry in data]

            if not temperature_values:
                print("Nessun dato di temperatura disponibile.")
                time.sleep(60)
                continue  # Salta l'iterazione se non ci sono dati

            # Rimuovi outlier
            cleaned_temperatures = remove_outliers(temperature_values)

            # Calcola statistiche per i dati attuali
            variance, stddev = calculate_variance_stddev(cleaned_temperatures)
            slope = linear_trend(cleaned_temperatures)
            current_stats = calculate_statistics(cleaned_temperatures)

            if current_stats:
                # Prepara le statistiche per la pubblicazione
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

                # Pubblica le statistiche su MQTT
                self.mqtt_client.myPublish("statistics/temperature", stats_to_publish)

                # Pubblica le statistiche su InfluxDB
                self.write_to_influxdb(stats_to_publish, topic_name)

            # Attendi prima di ripubblicare le statistiche
            time.sleep(60)

    def write_to_influxdb(self, stats, topic):
        """Scrivi le statistiche in InfluxDB."""
        self.influxdb_adaptor.write_data(
            measurement_name="temperature_statistics",
            tags={
                "host": "MacBook-Pro-di-luca-3.local",
                "topic": "GreenBox/d1/s1/temperature/statistics"
            },
            fields={
                "mean_temperature": stats["mean_temperature"],
                "min_temperature": stats["min_temperature"],
                "max_temperature": stats["max_temperature"],
                "variance": stats["variance"],
                "stddev": stats["stddev"],
                "slope_of_trend": stats["slope_of_trend"]
            },
            timestamp=int(stats["timestamp"] * 1000)  # Timestamp in millisecondi
        )


if __name__ == "__main__":
    # Carica le variabili d'ambiente dal file .env (opzionale, se usi python-dotenv)
    influxdb_adaptor = InfluxDBAdaptor(
        bucket=os.environ.get("INFLUXDB_BUCKET"),
        org=os.environ.get("INFLUXDB_ORG"),
        token=os.environ.get("INFLUX_TOKEN"),
        url=os.environ.get("INFLUXDB_URL")
    )

    mqtt_client = MyMQTT(clientID="TemperatureStatsPublisher", broker="localhost", port=1883)
    mqtt_client.start()

    temperature_statistics = TemperatureStatistics(
        influxdb_adaptor=influxdb_adaptor,
        mqtt_client=mqtt_client
    )

    temperature_statistics.publish_statistics(
        measurement_name="mqtt_consumer",
        field_name="temperature",
        host_name="MacBook-Pro-di-luca-3.local",
        topic_name="GreenBox/d1/s1/temperature"
    )
