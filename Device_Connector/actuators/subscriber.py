import json
import time
from Raspberry_Connector.tools.my_mqtt import MyMQTT


def handle_message(topic, payload):
    print("Received statistics from topic:", topic)
    statistics = json.loads(payload)
    print("Statistics:", json.dumps(statistics, indent=4))


class MyMQTTExtended(MyMQTT):
    def notify(self, topic, payload):
        # Decodifica il payload da bytes a string
        decoded_payload = payload.decode()
        # Usa il gestore di messaggi personalizzato
        handle_message(topic, decoded_payload)


# Configurazione del broker MQTT
broker_address = "localhost"
broker_port = 1883
client_id = "statistics_subscriber"

# Crea un'istanza di MyMQTTExtended
mqtt_subscriber = MyMQTTExtended(client_id, broker_address, broker_port)

# Avvia la connessione al broker
mqtt_subscriber.start()

try:
    # Iscriviti al topic "statistics"
    mqtt_subscriber.mySubscribe("statistics")

    print("Listening for statistics...")
    # Mantieni il programma in esecuzione per poter ricevere messaggi
    while True:
        time.sleep(1)  # Riduce il carico della CPU

except KeyboardInterrupt:
    print("Stopping subscriber...")
    mqtt_subscriber.stop()