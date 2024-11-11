class Device:
    def __init__(self, device_id, device_cathegory, device_name):
        self.id = device_id
        self.cathegory = device_cathegory
        self.name = device_name

    def jsonify(self):
        return {
            'device_id': self.id,
            'device_cathegory': self.cathegory,
            'device_name': self.name
        }

    @staticmethod
    def load(device_json: dict):
        return Device(device_id=device_json['id'],
                      device_cathegory=device_json['cathegory'],
                      device_name=device_json['name'])
