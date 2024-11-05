import time
import json
import os  # Per accedere alle variabili di ambiente
from influxdb_adaptor import InfluxDBAdaptor
from data_statistics import (
    moving_average, remove_outliers, calculate_variance_stddev, linear_trend,
    calculate_statistics
)
from tools.my_mqtt import MyMQTT


class HumidityStatistics:
    def __init__(self, influxdb_adaptor, mqtt_client):
        self.influxdb_adaptor = influxdb_adaptor
        self.mqtt_client = mqtt_client  # Istanza del client MQTT

    def publish_statistics(self, measurement_name, field_name, host_name, topic_name):
        while True:
            # Ottieni i dati dell'umidità dall'adaptor
            json_data = self.influxdb_adaptor.get_json_data(
                measurement_name, field_name, host_name, topic_name
            )
            data = json.loads(json_data)

            # Estrai i valori di umidità
            humidity_values = [entry['value'] for entry in data]

            if not humidity_values:
                print("Nessun dato di umidità disponibile.")
                time.sleep(60)
                continue  # Salta l'iterazione se non ci sono dati

            # Rimuovi outlier
            cleaned_humidity = remove_outliers(humidity_values)

            # Calcola statistiche per i dati attuali
            variance, stddev = calculate_variance_stddev(cleaned_humidity)
            slope = linear_trend(cleaned_humidity)
            current_stats = calculate_statistics(cleaned_humidity)

            if current_stats:
                # Prepara le statistiche per la pubblicazione
                timestamp = time.time()
                stats_to_publish = {
                    "timestamp": timestamp,
                    "mean_humidity": current_stats["mean"],
                    "min_humidity": current_stats["min"],
                    "max_humidity": current_stats["max"],
                    "variance": variance,
                    "stddev": stddev,
                    "slope_of_trend": slope
                }

                # Pubblica le statistiche su MQTT
                self.mqtt_client.myPublish("statistics/air_humidity", stats_to_publish)

                # Pubblica le statistiche su InfluxDB
                self.write_to_influxdb(stats_to_publish, topic_name)

            # Attendi prima di ripubblicare le statistiche
            time.sleep(60)

    def write_to_influxdb(self, stats, topic):
        """Scrivi le statistiche in InfluxDB."""
        self.influxdb_adaptor.write_data(
            measurement_name="humidity_statistics",
            tags={
                "host": "MacBook-Pro-di-luca-3.local",
                "topic": "GreenBox/d1/s1/air_humidity/statistics"
            },
            fields={
                "mean_humidity": stats["mean_humidity"],
                "min_humidity": stats["min_humidity"],
                "max_humidity": stats["max_humidity"],
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

    mqtt_client = MyMQTT(clientID="HumidityStatsPublisher", broker="localhost", port=1883)
    mqtt_client.start()

    humidity_statistics = HumidityStatistics(
        influxdb_adaptor=influxdb_adaptor,
        mqtt_client=mqtt_client
    )

    humidity_statistics.publish_statistics(
        measurement_name="mqtt_consumer",
        field_name="air_humidity",
        host_name="MacBook-Pro-di-luca-3.local",
        topic_name="GreenBox/d1/s1/air_humidity"
    )
