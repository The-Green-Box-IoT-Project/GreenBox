import logging
from concurrent.futures import ThreadPoolExecutor
import os
from Statistics.sensor_statistics.dht11_statistics import MeasurementStatistics as DHT11Stats
from Statistics.sensor_statistics.par_meter_statistics import MeasurementStatistics as PARStats
from Statistics.sensor_statistics.ph_meter_statistics import MeasurementStatistics as PHStats
from Statistics.sensor_statistics.soil_humidity_statistics import MeasurementStatistics as SoilHumidityStats
from Statistics.influxdb_adaptor import InfluxDBAdaptor
from Statistics.tools.my_mqtt import MyMQTT

# Setup logging
logging.basicConfig(level=logging.INFO)

# Configurazione dei parametri InfluxDB e MQTT
influxdb_adaptor = InfluxDBAdaptor(
    bucket=os.environ.get("INFLUXDB_BUCKET"),
    org=os.environ.get("INFLUXDB_ORG"),
    token=os.environ.get("INFLUX_TOKEN"),
    url=os.environ.get("INFLUXDB_URL")
)

mqtt_client = MyMQTT(clientID="StatsControlBoard", broker="localhost", port=1883)
mqtt_client.start()

# Definizione dei topic di base per ogni sensore
client_id = "01f20b9e-6df4-43df-9fd6-c1376bb2ba41"
greenhouse_id = "greenhouse1"
raspberry_id = "rb01"

# Instanziazione delle classi di statistiche per ogni sensore
dht11_stats = DHT11Stats(
    influxdb_adaptor=influxdb_adaptor,
    mqtt_client=mqtt_client,
    base_topic=f"/{client_id}/{greenhouse_id}/{raspberry_id}/measurements/dht11"
)

par_stats = PARStats(
    influxdb_adaptor=influxdb_adaptor,
    mqtt_client=mqtt_client,
    base_topic=f"/{client_id}/{greenhouse_id}/{raspberry_id}/measurements/par_meter"
)

ph_stats = PHStats(
    influxdb_adaptor=influxdb_adaptor,
    mqtt_client=mqtt_client,
    base_topic=f"/{client_id}/{greenhouse_id}/{raspberry_id}/measurements/ph_meter"
)

soil_humidity_stats = SoilHumidityStats(
    influxdb_adaptor=influxdb_adaptor,
    mqtt_client=mqtt_client,
    base_topic=f"/{client_id}/{greenhouse_id}/{raspberry_id}/measurements/grodan"
)


# Funzione per avviare la pubblicazione delle statistiche di ogni sensore
def start_publishing_statistics(statistics_obj, measurement_name, host_name, measurement_types):
    statistics_obj.publish_statistics(
        measurement_name=measurement_name,
        host_name=host_name,
        measurement_types=measurement_types
    )


# Esegui la raccolta e la pubblicazione dei dati per ciascun sensore in parallelo
if __name__ == "__main__":
    try:
        with ThreadPoolExecutor(max_workers=4) as executor:
            # Avvia un thread per ciascun sensore
            executor.submit(start_publishing_statistics, dht11_stats, "mqtt_consumer", "MBP-di-luca-3.lan",
                            ["temperature", "humidity"])
            executor.submit(start_publishing_statistics, par_stats, "mqtt_consumer", "MBP-di-luca-3.lan", ["light"])
            executor.submit(start_publishing_statistics, ph_stats, "mqtt_consumer", "MBP-di-luca-3.lan", ["pH"])
            executor.submit(start_publishing_statistics, soil_humidity_stats, "mqtt_consumer", "MBP-di-luca-3.lan",
                            ["soil_humidity"])
    except KeyboardInterrupt:
        print("Interruption received, stopping the statistics control board.")
        mqtt_client.stop()
