# Importa la classe MyMQTT
<<<<<<< HEAD
from Raspberry_Connector.tools.my_mqtt import MyMQTT
import time
import json

#
# # Funzione per la gestione dei messaggi ricevuti
# def handle_message(topic, payload):
#     print("Received message from topic:", topic)
#     print("Message:", payload)
#
#
# # Configurazione del broker MQTT
# broker_address = "localhost"
# broker_port = 1883
# client_id = "RaspberryConnector"
#
# # Crea un'istanza di MyMQTT
# mqtt_subscriber = MyMQTT(client_id, broker_address, broker_port)
#
# # Avvia la connessione al broker
# mqtt_subscriber.start()
#
# try:
#     # Iscriviti al topic "sensor/data"
#     mqtt_subscriber.mySubscribe("GreenBox/d1/s1/temperature")
#
#     while True:
#         # Continua ad ascoltare i messaggi
#         pass
#
# except KeyboardInterrupt:
#     print("Stopping subscriber...")
#     mqtt_subscriber.stop()


def handle_message(topic, payload):
    print("Received statistics from topic:", topic)
    statistics = json.loads(payload)
    print("Temperature:", json.dumps(statistics, indent=4))


class MyMQTTExtended(MyMQTT):
    def notify(self, topic, payload):
        # Decodifica il payload da bytes a string
        decoded_payload = payload.decode()
        # Usa il gestore di messaggi personalizzato
        handle_message(topic, decoded_payload)
=======
from Device_Connector.sensors.modules.my_mqtt import MyMQTT


# Funzione per la gestione dei messaggi ricevuti
def handle_message(topic, payload):
    print("Received message from topic:", topic)
    print("Message:", payload)
>>>>>>> 00ef6ca (Created DHT11 and Grodan sensors objects.)


# Configurazione del broker MQTT
broker_address = "localhost"
broker_port = 1883
<<<<<<< HEAD
client_id = "RaspberryConnector"

# Crea un'istanza di MyMQTTExtended
mqtt_subscriber = MyMQTTExtended(client_id, broker_address, broker_port)
=======
client_id = "subscriber_client"

# Crea un'istanza di MyMQTT
mqtt_subscriber = MyMQTT(client_id, broker_address, broker_port)
>>>>>>> 00ef6ca (Created DHT11 and Grodan sensors objects.)

# Avvia la connessione al broker
mqtt_subscriber.start()

try:
<<<<<<< HEAD
    # Iscriviti al topic "statistics"
    mqtt_subscriber.mySubscribe("statistics")

    print("Listening for data...")
    # Mantieni il programma in esecuzione per poter ricevere messaggi
    while True:
        time.sleep(1)  # Riduce il carico della CPU
=======
    # Iscriviti al topic "sensor/data"
    mqtt_subscriber.mySubscribe("sensor/data")

    while True:
        # Continua ad ascoltare i messaggi
        pass
>>>>>>> 00ef6ca (Created DHT11 and Grodan sensors objects.)

except KeyboardInterrupt:
    print("Stopping subscriber...")
    mqtt_subscriber.stop()
