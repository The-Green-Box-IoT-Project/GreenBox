import json
import time
from subscriber import MyMQTT

class Actuator:
    def __init__(self, conf_path, actuator_type, metric_name):
        # Carica le configurazioni
        with open(conf_path) as f:
            self.conf_dict = json.load(f)

        self.actuator_type = actuator_type  # Es: 'heating', 'cooling'
        self.metric_name = metric_name  # Es: 'temperature', 'air_humidity'
        self.broker_ip = self.conf_dict["broker_ip"]
        self.broker_port = self.conf_dict["broker_port"]

        # Configura MQTT per sottoscriversi al topic specifico
        clientID = f"{actuator_type}_{metric_name}_Actuator"
        self._pubSub = MyMQTT(clientID=clientID, broker=self.broker_ip, port=self.broker_port, notifier=self)
        self._pubSub.start()

        # Sottoscrivi al topic dei comandi per l'attuatore specifico
        self.topic = f"GreenBox/actuators/{self.metric_name}/{self.actuator_type}"
        self._pubSub.mySubscribe(self.topic)
        print(f"{actuator_type.capitalize()} actuator for {metric_name} subscribed to topic: {self.topic}")

    def notify(self, topic, message):
        # Callback chiamato ogni volta che l'attuatore riceve un comando
        data = json.loads(message)
        command = data.get("command")
        activate = data.get("activate")

        if activate:
            print(f"{self.actuator_type.capitalize()} actuator for {self.metric_name}: ACTIVATED")
            self.activate()
        else:
            print(f"{self.actuator_type.capitalize()} actuator for {self.metric_name}: DEACTIVATED")
            self.deactivate()

    def activate(self):
        # Azione di attivazione simulata
        print(f"Simulating activation of {self.actuator_type} for {self.metric_name}...")

    def deactivate(self):
        # Azione di disattivazione simulata
        print(f"Simulating deactivation of {self.actuator_type} for {self.metric_name}...")


if __name__ == "__main__":
    # Crea istanze degli attuatori
    heating_actuator = Actuator(
        conf_path="Control_Strategies/config.json",
        actuator_type="heating",
        metric_name="temperature"
    )

    cooling_actuator = Actuator(
        conf_path="Control_Strategies/config.json",
        actuator_type="cooling",
        metric_name="temperature"
    )

    # Mantiene gli attuatori in esecuzione per ricevere comandi
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("Attuatori fermati.")
