# def create_list_of_measurements(self, index):
#     list_of_measurements = []
#     for sensor in self.sensors_list:
#         if sensor == self.dht11:
#             for i in sensor.measurement_type:
#                 if i == "temperature":
#                     measurement = {"topic": sensor.topic_temperature, "data_json": {"temperature": sensor.temperature}}
#                 else:
#                     measurement = {"topic": sensor.topic_air_humidity, "data_json": {"air_humidity": sensor.air_humidity}}
#                 list_of_measurements.append(measurement)
#         else:
#             measurement = {"topic": sensor.topic, "data_json": {sensor.measurement_type: sensor.dataframe}}  # TODO: trova un modo per generalizzare sensor.dataframe, ora è sbagliato.
#             list_of_measurements.append(measurement)
#     return list_of_measurements

# def create_list_of_measurements(self, index):
#     list_of_measurements = [
#         {
#             "topic": self.dht11.topic_temperature,
#             "data_json": {
#                 "temperature": self.dht11.temperature.iloc[index],
#             }
#         },
#         {
#             "topic": self.dht11.topic_air_humidity,
#             "data_json": {
#                 "air_humidity": self.dht11.air_humidity.iloc[index],
#             }
#         },
#         {
#             "topic": self.pH_meter.topic,
#             "data_json": {
#                 self.pH_meter.measurement_type: self.pH_meter.pH.iloc[index],
#             }
#         },
#         {
#             "topic": self.PAR_meter.topic,
#             "data_json": {
#                 self.PAR_meter.measurement_type: self.PAR_meter.PAR.iloc[index],
#             }
#         },
#         {
#             "topic": self.grodan.topic,
#             "data_json": {
#                 self.grodan.measurement_type: self.grodan.soil_humidity.iloc[index],
#             }
#         }
#     ]
#     return list_of_measurements
