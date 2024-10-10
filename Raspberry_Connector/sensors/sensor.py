import sensors_interface


class Sensor:
    def __init__(self):
        self.device_id, self.catalog_ip, self.catalog_port = sensors_interface.retrieve_config()

