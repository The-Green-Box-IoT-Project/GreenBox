import time
import random
from Raspberry_Connector.raspberry_connector import RaspberryConnector
from Raspberry_Connector.tools.my_mqtt import MyMQTT


# Funzione per generare dati casuali
def generate_random_data():
    temperature = random.uniform(20, 30)
    humidity = random.uniform(40, 60)
    return {"temperature": temperature, "humidity": humidity}


# Configurazione del broker MQTT
broker_address = "localhost"
broker_port = 1883
client_id = "publisher_client"

# Crea un'istanza di MyMQTT
mqtt_publisher = MyMQTT(client_id, broker_address, broker_port)


# Avvia la connessione al broker
mqtt_publisher.start()

try:
    sec = 0
    while True:

        data = generate_random_data()

        # Invia i dati al topic "sensor/data"
        mqtt_publisher.myPublish("sensor/data", data)

        print("Data sent:", data)

        # Attendi per un intervallo di tempo casuale (da 1 a 5 secondi)
        time.sleep(random.uniform(1, 5))
        sec += 1

except KeyboardInterrupt:
    print("Stopping publisher...")
    mqtt_publisher.stop()
