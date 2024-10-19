from Raspberry_Connector.sensors import sensors_interface


def hardware_read(pin):
    pass  # TODO


class Sensor:
    def __init__(self, config_path):
        device_id, device_name, device_pin, measurements = sensors_interface.retrieve_sensor(config_path)
        self.device_id = device_id
        self.device_name = device_name
        self.device_pin = device_pin
        self.measurements = measurements

    def read_value(self):
        return hardware_read(self.device_pin)

    def _build_topics(self, parent_topic):
        return (f"""{parent_topic}/{self.device_id}/{m['topic']}""" for m in self.measurements)
