import time
import json
from influxdb_adaptor import InfluxDBAdaptor
from data_statistics import (
    remove_outliers, calculate_variance_stddev, linear_trend,
    calculate_statistics, compare_with_historical_in_chunks
)
from tools.my_mqtt import MyMQTT


class AirHumidityStatistics:
    def __init__(self, influxdb_adaptor, historical_file, mqtt_client):
        self.influxdb_adaptor = influxdb_adaptor
        self.historical_file = historical_file
        self.mqtt_client = mqtt_client  # Istanza del client MQTT

    def publish_statistics(self, measurement_name, field_name, host_name, topic_name):
        while True:
            # Ottieni i dati dell'umidità dall'adaptor
            json_data = self.influxdb_adaptor.get_json_data(
                measurement_name, field_name, host_name, topic_name
            )
            data = json.loads(json_data)

            # Estrai i valori dell'umidità
            humidity_values = [entry['value'] for entry in data]

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
                self.mqtt_client.myPublish("statistics/humidity", stats_to_publish)

                # Confronta con i dati storici e pubblica il confronto
                comparison = compare_with_historical_in_chunks(
                    self.historical_file, current_stats, variance, slope, cleaned_humidity
                )
                if comparison:
                    self.mqtt_client.myPublish("statistics/humidity/comparison", comparison)

            # Attendi prima di ripubblicare le statistiche
            time.sleep(60)


if __name__ == "__main__":
    influxdb_adaptor = InfluxDBAdaptor(
        bucket="Box1",
        org="GreenBox",
        token="smHyTmK0VIHnSQxAkDW_Hf8-fMvVjxxDbfrUPuD7VR6ejbbOULxHZREECno9UwwhX8F9X_gUbIC8eWYGE9ykog==",
        url="http://localhost:8086"
    )

    mqtt_client = MyMQTT(clientID="AirHumidityStatsPublisher", broker="localhost", port=1883)
    mqtt_client.start()

    air_humidity_statistics = AirHumidityStatistics(
        influxdb_adaptor,
        historical_file='../mock_data_final.json',
        mqtt_client=mqtt_client
    )

    air_humidity_statistics.publish_statistics(
        measurement_name="mqtt_consumer",
        field_name="humidity",
        host_name="MBP-di-luca-2.lan",
        topic_name="GreenBox/d1/s1/humidity"
    )
