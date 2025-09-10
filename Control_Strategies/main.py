import time
import json
from control_module import ControlModule
from tools.my_mqtt import MyMQTT

# Configurazione del broker MQTT
BROKER_IP = "localhost"
BROKER_PORT = 1883

# Definisci l'ID del Raspberry Pi corrente
raspberry_id = "rb01"

# Carica la configurazione del client dal file strategies.json
with open("strategies.json", "r") as f:
    strategies = json.load(f)

# Trova la configurazione del client basata su raspberry_id
client = None
for c in strategies["clients"]:
    if c["raspberry_id"] == raspberry_id:
        client = c
        break

if client is None:
    raise ValueError(f"Raspberry Pi con ID '{raspberry_id}' non trovato in strategies.json.")

# Estrai gli identificatori necessari
client_id = client.get("client_id", "default_client_id")
greenhouse_id = client.get("greenhouse_id", "default_greenhouse_id")

# Costruisci il topic base dinamicamente
base_topic = f"/{client_id}/{greenhouse_id}/{raspberry_id}"

# Crea un set di metriche da sottoscrivere basato sulle soglie degli attuatori
metrics = set()
for actuator in client.get("actuators", []):
    for metric in actuator["thresholds"].keys():
        metrics.add(metric)

# Mappa le metriche ai topic dei sensori corrispondenti
metric_to_topic_map = {
    "temperature": f"{base_topic}/statistics/dht11/temperature",
    "humidity": f"{base_topic}/statistics/dht11/humidity",
    "light": f"{base_topic}/statistics/par_meter",
    "soil_humidity": f"{base_topic}/statistics/grodan",
    "pH": f"{base_topic}/statistics/ph_meter"
}

# Definisci tutti i topic di interesse per le varie statistiche basate sulle metriche necessarie
topics = {metric: topic for metric, topic in metric_to_topic_map.items() if metric in metrics}

# Crea il client MQTT
mqtt_client = MyMQTT(clientID="GreenhouseControl", broker=BROKER_IP, port=BROKER_PORT)

# Crea il modulo di controllo per il Raspberry Pi specifico
control_module = ControlModule(mqtt_client, raspberry_id, base_topic)

# Imposta il modulo di controllo nel client MQTT
mqtt_client.set_control_module(control_module)

# Avvia il client MQTT e sottoscrivi tutti i topic rilevanti delle statistiche
mqtt_client.start()
for topic in topics.values():
    mqtt_client.mySubscribe(topic)

# Mantieni il programma in esecuzione
try:
    while True:
        time.sleep(30)
except KeyboardInterrupt:
    print("Interruzione ricevuta, fermo il client MQTT")
    mqtt_client.stop()
