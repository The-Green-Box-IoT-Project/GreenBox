
import json
import paho.mqtt.client as mqtt


class MyMQTT:
    def __init__(self, clientID, broker, port, notifier=None):
        self.broker = broker
        self.port = port
        self.notifier = notifier if notifier else self.notify  # Usa notifier passato o il metodo notify di default
        self.clientID = clientID
        self._topic = ""
        self._isSubscriber = False
        self._control_module = None  # Aggiunge un riferimento al modulo di controllo

        # Crea un'istanza di paho.mqtt.client
        self._paho_mqtt = mqtt.Client(mqtt.CallbackAPIVersion.VERSION1, clientID)
        # register the callback
        self._paho_mqtt.on_connect = self.myOnConnect
        self._paho_mqtt.on_message = self.myOnMessageReceived

    def set_control_module(self, control_module):
        """
        Assegna il modulo di controllo che verrà notificato con le statistiche.
        :param control_module: Istanza del modulo di controllo
        """
        self._control_module = control_module

    @staticmethod
    def notify(topic, payload):
        print(f"Received message on topic '{topic}': {payload}")

    def myOnConnect(self, client, userdata, flags, reason_code, properties=None):
        if reason_code == 0:
            print(f"Connected to {self.broker} with success.")
        else:
            print(f"Connection failed with reason code: {reason_code}")

    def myOnMessageReceived(self, client, userdata, message):
        """
        Callback chiamato quando si riceve un nuovo messaggio MQTT.
        Se il modulo di controllo è configurato, inoltra il messaggio al modulo di controllo.
        """
        payload = message.payload.decode('utf-8')

        if self._control_module:
            # Passa le statistiche al modulo di controllo
            data = json.loads(payload)
            self._control_module.analyze_statistics(data)

    def myPublish(self, topic, msg):
        """
        Pubblica un messaggio su un certo topic.
        :param topic: Topic MQTT su cui pubblicare
        :param msg: Messaggio da pubblicare (dizionario)
        """
        print(f"Publishing message on topic '{topic}': {msg}")
        self._paho_mqtt.publish(topic, json.dumps(msg), qos=2)

    def mySubscribe(self, topic):
        """
        Sottoscrivi al topic specificato.
        :param topic: Topic MQTT a cui sottoscriversi
        """
        self._paho_mqtt.subscribe(topic, qos=2)
        self._isSubscriber = True
        self._topic = topic
        print(f"Subscribed to topic: {topic}")

    def start(self):
        """
        Gestisce la connessione al broker.
        """
        self._paho_mqtt.connect(self.broker, self.port)
        self._paho_mqtt.loop_start()

    def stop(self):
        """
        Ferma la connessione MQTT e annulla la sottoscrizione.
        """
        if self._isSubscriber:
            self._paho_mqtt.unsubscribe(self._topic)
        self._paho_mqtt.loop_stop()
        self._paho_mqtt.disconnect()
