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

from raspberry_connector import RaspberryConnector

rc = RaspberryConnector(conf_path="conf.json", devices_path="devices.json", seconds=3)
rc.publish_last_measurements()
