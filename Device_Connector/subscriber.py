# Importa la classe MyMQTT
from Device_Connector.sensors.modules.MyMQTT import MyMQTT


# Funzione per la gestione dei messaggi ricevuti
def handle_message(topic, payload):
    print("Received message from topic:", topic)
    print("Message:", payload)


# Configurazione del broker MQTT
broker_address = "localhost"
broker_port = 1883
client_id = "subscriber_client"

# Crea un'istanza di MyMQTT
mqtt_subscriber = MyMQTT(client_id, broker_address, broker_port)

# Avvia la connessione al broker
mqtt_subscriber.start()

try:
    # Iscriviti al topic "sensor/data"
    mqtt_subscriber.mySubscribe("sensor/data")

    while True:
        # Continua ad ascoltare i messaggi
        pass

except KeyboardInterrupt:
    print("Stopping subscriber...")
    mqtt_subscriber.stop()
