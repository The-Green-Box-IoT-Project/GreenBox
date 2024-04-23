<<<<<<< HEAD
import time
import random
from Raspberry_Connector.raspberry_connector import RaspberryConnector
from Raspberry_Connector.tools.my_mqtt import MyMQTT


# Funzione per generare dati casuali
def generate_random_data():
    temperature = random.uniform(20, 30)
    humidity = random.uniform(40, 60)
    return {"temperature": temperature, "humidity": humidity}
#
#
# def read_sensor_data(path):
#     data = pd.read_csv(path)
#     df = dht11_sensor(data)
#     df = correct_non_numeric_values(df)
#     df = resample_dataframe(df, 6)
#     return df
#
#
# def data_correct_format(row):
#     temperature = row['temperature']
#     humidity = row['humidity']
#     return {"temperature": temperature, "humidity": humidity}


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

        # path = 'sensors/data/dataset/GreenhouseClimate.csv'
        # dataframe = read_sensor_data(path)
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
=======
# # # import time
# # # import random
# # # from Device_Connector.sensors.modules.data_processor import *
# # # from Device_Connector.sensors.modules.MyMQTT import *
# # #
# # #
# # # # # Funzione per generare dati casuali
# # # # def generate_random_data():
# # # #     temperature = random.uniform(20, 30)
# # # #     humidity = random.uniform(40, 60)
# # # #     return {"temperature": temperature, "humidity": humidity}
# # #
# # #
# # # def read_sensor_data(path):
# # #     data = pd.read_csv(path)
# # #     df = dht11_sensor(data)
# # #     df = correct_non_numeric_values(df)
# # #     df = resample_dataframe(df, 6)
# # #     return df
# # #
# # #
# # # def data_correct_format(row):
# # #     temperature = row['temperature']
# # #     humidity = row['humidity']
# # #     return {"temperature": temperature, "humidity": humidity}
# # #
# # #
# # # # Configurazione del broker MQTT
# # # broker_address = "localhost"
# # # broker_port = 1883
# # # client_id = "publisher_client"
# # #
# # # # Crea un'istanza di MyMQTT
# # # mqtt_publisher = MyMQTT(client_id, broker_address, broker_port)
# # #
# # #
# # # # Avvia la connessione al broker
# # # mqtt_publisher.start()
# # #
# # # try:
# # #     sec = 0
# # #     while True:
# # #
# # #         path = 'sensors/data/dataset/GreenhouseClimate.csv'
# # #         dataframe = read_sensor_data(path)
# # #         data = data_correct_format(dataframe.iloc[sec])
# # #
# # #         # Invia i dati al topic "sensor/data"
# # #         mqtt_publisher.myPublish("sensor/data", data)
# # #
# # #         print("Data sent:", data)
# # #
# # #         # Attendi per un intervallo di tempo casuale (da 1 a 5 secondi)
# # #         time.sleep(random.uniform(1, 5))
# # #         sec += 1
# # #
# # # except KeyboardInterrupt:
# # #     print("Stopping publisher...")
# # #     mqtt_publisher.stop()
# #
# #
# # from sensors.dht11 import DHT11
# # from sensors.modules.my_mqtt import *
# # import time
# # import random
# #
# # # Configurazione del broker MQTT
# # broker_address = "localhost"
# # broker_port = 1883
# # client_id = "publisher_client"
# #
# #
# # class DeviceConnector:
# #     def __init__(self, broker_address, broker_port, client_id):
# #         self.dht11 = DHT11()
# #         self.broker_address = broker_address
# #         self.broker_port = broker_port
# #         self.client_id = client_id
# #
# #     def create_mqtt_instance(self):
# #         mqtt_instance = MyMQTT(self.client_id, self.broker_address, self.broker_port)
# #         return mqtt_instance
# #
# #     @staticmethod
# #     def data_correct_format(row):
# #         temperature = row['temperature']
# #         humidity = row['humidity']
# #         return {"temperature": temperature, "humidity": humidity}
# #
# #     def read_dht11_data(self, sec):
# #         dht11_data = self.dht11.data
# #         dht11_data = self.data_correct_format(dht11_data.iloc[sec])
# #         return dht11_data
# #
# #     def publish(self):
# #         mqtt_publisher = self.create_mqtt_instance()
# #         mqtt_publisher.start()
# #
# #         try:
# #             sec = 0
# #             while True:
# #                 data = self.read_dht11_data(sec)
# #
# #                 # Invia i dati al topic "sensor/data"
# #                 mqtt_publisher.myPublish("sensor/data", data)
# #
# #                 print("Data sent:", data)
# #
# #                 # Attendi per un intervallo di tempo casuale (da 1 a 5 secondi)
# #                 time.sleep(random.uniform(1, 5))
# #                 sec += 1
# #
# #         except KeyboardInterrupt:
# #             print("Stopping publisher...")
# #             mqtt_publisher.stop()
# #             print("Publisher stopped.")
# #
# #
# # if __name__ == "__main__":
# #     dc = DeviceConnector(broker_address, broker_port, client_id)
# #     dc.publish()
#
# from sensors.dht11 import DHT11
# from sensors.modules.my_mqtt import *
# import time
# import random
#
# # Configurazione del broker MQTT
# broker_address = "localhost"
# broker_port = 1883
# client_id = "publisher_client"
#
#
# class DeviceConnector:
#     def __init__(self, broker_address, broker_port, client_id):
#
#         self.broker_address = broker_address
#         self.broker_port = broker_port
#         self.client_id = client_id
#         self.data_sources = {}  # Dictionary to store data sources and topics
#         self.data_format_funcs = {}  # Dictionary to store data formatting functions
#
#     def create_mqtt_instance(self):
#         mqtt_instance = MyMQTT(self.client_id, self.broker_address, self.broker_port)
#         return mqtt_instance
#
#     @staticmethod
#     def data_correct_format(row):
#         output_row = {}
#         for col_name, value in row.items():
#             output_row[col_name] = value
#         return output_row
#
#     def read_dht11_data(self):
#         try:
#             # Attempt to read DHT11 sensor data
#             dht11 = DHT11()
#             data = dht11.read()
#             if data is not False:
#                 return data
#             else:
#                 print("Failed to read DHT11 sensor data")
#                 return None
#         except Exception as e:
#             print("Error reading DHT11 sensor:", e)
#             return None
#
#     def add_data_source(self, sensor_name, data_source, topic_prefix, data_format_func):
#         # Extract sensor type from sensor name (e.g., "dht11/temperature")
#         sensor_type = sensor_name.split("/")[1]
#
#         self.data_sources[sensor_name] = data_source
#         self.data_format_funcs[sensor_name] = data_format_func
#
#         # Create topic for the specific sensor type (e.g., "dht11/humidity")
#         topic = f"{topic_prefix}/{sensor_type}"
#         self.topics[topic] = sensor_name
#
#     def publish(self):
#         # Attempt to connect and publish data with error handling
#         try:
#             mqtt_publisher = self.create_mqtt_instance()
#             mqtt_publisher.start()
#
#             while True:
#                 for sensor_name, data_source in self.data_sources.items():
#                     if data_source:
#                         data = data_source()  # Get data from the source
#                         topic = self.topics[sensor_name]  # Get corresponding topic
#                         data_json = self.data_format_funcs[sensor_name](data)  # Format data
#                         mqtt_publisher.myPublish(topic, data_json)
#                         print(f"Data sent ({sensor_name}): {data_json}")
#                 time.sleep(1)
#
#         except KeyboardInterrupt:
#             print("Stopping publisher...")
#         except Exception as e:
#             print("Error during publishing:", e)
#         finally:
#             if mqtt_publisher:
#                 mqtt_publisher.stop()
#             print("Publisher stopped.")
#
#
# if __name__ == "__main__":
#     dc = DeviceConnector(broker_address, broker_port, client_id)
#
#     # Example usage for DHT11 data on separate topics
#     dc.add_data_source("dht11/temperature", dc.read_dht11_data, "dht11", dc.data_correct_format)
#     dc.add_data_source("dht11/humidity", dc.read_dht11_data, "dht11", dc.data_correct_format)
#
#     # Example usage for rain sensor data on "ac1/rain" topic
#     def rain_sensor_data_source():
#         # Simulate rain sensor data
#         rain_level = random.randint(0, 100)  # Simulate rain level (0-100)
#         return {"rain_level": rain_level}
#
#     def rain_sensor_data_format
>>>>>>> 00ef6ca (Created DHT11 and Grodan sensors objects.)
