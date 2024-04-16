import pandas as pd
import time
import random
from modules.data_processor import *
from modules.MyMQTT import *


# Funzione per generare dati casuali
def generate_random_data():
    temperature = random.uniform(20, 30)
    humidity = random.uniform(40, 60)
    return {"temperature": temperature, "humidity": humidity}


def read_sensor_data(path):
    data = pd.read_csv(path)
    df = dht11_sensor(data)
    df = correct_non_numeric_values(df)
    df = resample_dataframe(df, 6)
    return df


def data_correct_format(row):
    temperature = row['temperature']
    humidity = row['humidity']
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

        path = './data/dataset/GreenhouseClimate.csv'
        dataframe = read_sensor_data(path)
        data = data_correct_format(dataframe.iloc[sec])

        # Invia i dati al topic "sensor/data"
        mqtt_publisher.myPublish("sensor/data", data)

        print("Data sent:", data)

        # Attendi per un intervallo di tempo casuale (da 1 a 5 secondi)
        time.sleep(random.uniform(1, 5))
        sec += 1

except KeyboardInterrupt:
    print("Stopping publisher...")
    mqtt_publisher.stop()
