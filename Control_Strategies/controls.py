import json
import requests
from tools.my_mqtt import MyMQTT
import time
import threading


class GreenBoxControl:
    def __init__(self, conf_path, metric_name, thresholds_endpoint):
        # Configurazione generale
        with open(conf_path) as f:
            self.conf_dict = json.load(f)

        self.metric_name = metric_name
        self.broker_ip = self.conf_dict["ip"]
        self.broker_port = self.conf_dict["port"]

        # self.addr_cat = f"http://{self.ip}:{self.port}"
        self.thresholds_endpoint = thresholds_endpoint
        self.thresholds = self.get_thresholds()
        self.track_actuation_dict = {}
        self._actuation_time = 5  # Durata standard dell'attuazione (in secondi)

        # Configura MQTT per comunicare con il broker
        clientID = f"{metric_name}Control-{int(time.time())}"
        self._pubSub = MyMQTT(clientID=clientID, broker=self.broker_ip, port=self.broker_port, notifier=self)
        self._pubSub.start()

        # Sottoscrivi al topic MQTT per la statistica della metrica specifica
        self.topic = f"GreenBox/statistics/{metric_name}"
        self._pubSub.mySubscribe(self.topic)
        print(f"Subscribed to topic: {self.topic}")

    def get_thresholds(self):
        # Recupera le soglie dal catalogo
        try:
            response = requests.get(f"{self.addr_cat}{self.thresholds_endpoint}")
            if response.status_code == 200:
                return response.json().get(f"{self.metric_name}_thresholds", {})
            else:
                print("Errore nel recupero delle soglie dal catalogo!")
        except Exception as e:
            print(f"Errore di connessione al catalogo: {e}")
            return {}

    def notify(self, topic, msg):
        # Callback di MQTT per gestire i messaggi di statistica
        data = json.loads(msg)

        # Esegui la logica di controllo basata sul valore specifico che desideri monitorare
        # Qui assumiamo che vogliamo monitorare `mean_temperature` per esempio
        value = data.get("mean_temperature")  # Cambia questo con il campo che vuoi monitorare

        if value is None:
            print(f"Valore {self.metric_name} non trovato nel messaggio: {data}")
            return

        # Verifica se il valore supera le soglie
        if value > self.thresholds["max"]:
            self.send_command_to_actuator("cooling", True)
        elif value < self.thresholds["min"]:
            self.send_command_to_actuator("heating", True)
        else:
            self.stop_actuation("cooling")
            self.stop_actuation("heating")

    def send_command_to_actuator(self, command, activate):
        # Pubblica il comando all'attuatore specifico
        message = {
            "command": command,
            "activate": activate,
            "timestamp": time.time()
        }
        actuator_topic = f"GreenBox/actuators/{self.metric_name}/{command}"
        self._pubSub.myPublish(actuator_topic, message)
        print(f"Comando inviato all'attuatore: {message}")

        # Traccia l'attivazione dell'attuatore
        if activate:
            self.track_actuation_dict[command] = threading.Timer(self._actuation_time, self.stop_actuation,
                                                                 args=(command,))
            self.track_actuation_dict[command].start()

    def stop_actuation(self, command):
        # Ferma l'attuazione dell'attuatore
        actuator_topic = f"GreenBox/actuators/{self.metric_name}/{command}"
        message = {
            "command": command,
            "activate": False,
            "timestamp": time.time()
        }
        self._pubSub.myPublish(actuator_topic, message)
        print(f"Comando di stop inviato all'attuatore: {message}")

        # Rimuovi il timer
        if command in self.track_actuation_dict:
            self.track_actuation_dict.pop(command)


if __name__ == "__main__":
    # Istanza di controllo per la temperatura
    temperature_control = GreenBoxControl(
        conf_path="config.json",
        metric_name="temperature",
        thresholds_endpoint="/getThresholds?parameter=temperature"
    )

    # Istanza di controllo per l'umidità dell'aria
    air_humidity_control = GreenBoxControl(
        conf_path="config.json",
        metric_name="air_humidity",
        thresholds_endpoint="/getThresholds?parameter=air_humidity"
    )

    # Mantieni il programma in esecuzione
    while True:
        time.sleep(30)
