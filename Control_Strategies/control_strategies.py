import time


class ControlStrategy:
    def __init__(self, thresholds, mqtt_client, base_topic):
        self.thresholds = thresholds
        self.mqtt_client = mqtt_client
        self.base_topic = base_topic

    def analyze_statistics(self, statistics):
        raise NotImplementedError("Implement this method in the subclass.")


class BasicControlStrategy(ControlStrategy):
    def __init__(self, thresholds, mqtt_client, base_topic):
        super().__init__(thresholds, mqtt_client, base_topic)
        self.in_range_counter = 0  # Counter for consecutive in-range readings
        self.cooling_active = False
        self.heating_active = False

    def analyze_statistics(self, statistics):
        mean_temp = statistics.get("mean_temperature")

        if mean_temp is None:
            print("[ERROR] Campo 'mean_temperature' mancante.")
            return

        # Attiva cooling se la temperatura è sopra la soglia massima
        if mean_temp > self.thresholds["max"]:
            if not self.cooling_active:
                print("[DEBUG] Superata soglia massima, attivazione raffreddamento.")
                print(f"[ALERT] Valori delle statistiche fuori norma: {statistics}")
                self.send_command("cooling", True)
                self.cooling_active = True
                self.heating_active = False
            self.in_range_counter = 0  # Resetta il contatore se fuori dai limiti

        # Attiva heating se la temperatura è sotto la soglia minima
        elif mean_temp < self.thresholds["min"]:
            if not self.heating_active:
                print("[DEBUG] Superata soglia minima, attivazione riscaldamento.")
                self.send_command("heating", True)
                self.heating_active = True
                self.cooling_active = False
            self.in_range_counter = 0  # Resetta il contatore se fuori dai limiti

        # La temperatura è nei limiti
        else:
            if self.cooling_active or self.heating_active:
                self.in_range_counter += 1
                print(f"[DEBUG] Temperatura nei limiti per {self.in_range_counter} rilevamenti consecutivi.")

                # Disattiva gli attuatori solo dopo 3 rilevamenti consecutivi nei limiti
                if self.in_range_counter >= 3:
                    print("[DEBUG] 3 rilevamenti consecutivi nei limiti, disattivazione attuatori.")
                    self.send_command("cooling", False)
                    self.send_command("heating", False)
                    self.cooling_active = False
                    self.heating_active = False
                    self.in_range_counter = 0  # Resetta il contatore dopo disattivazione
            else:
                self.in_range_counter = 0  # Resetta se non ci sono attuatori attivi

    def send_command(self, command, activate):
        message = {
            "command": command,
            "activate": activate,
            "timestamp": time.time()
        }
        # **Construct the actuator topic dynamically**
        topic = f"{self.base_topic}/actuators/{command}"
        print(f"[DEBUG] Tentativo di invio comando: {command}, attivazione: {activate} sul topic: {topic}")
        self.mqtt_client.myPublish(topic, message)


class AdvancedControlStrategy(ControlStrategy):
    def __init__(self, thresholds, mqtt_client, base_topic):
        super().__init__(thresholds, mqtt_client, base_topic)
        self.in_range_counter = 0  # Counter for consecutive in-range readings
        self.cooling_active = False
        self.heating_active = False

    def analyze_statistics(self, statistics):
        mean_temp = statistics.get("mean_temperature")
        stddev = statistics.get("stddev", 0)  # Devi sapere se stddev è disponibile

        if mean_temp is None:
            print("[ERROR] Campo 'mean_temperature' mancante.")
            return

        # Attiva cooling se la temperatura è sopra la soglia massima e stddev > 0.5
        if mean_temp > self.thresholds["max"] and stddev > 0.5:
            if not self.cooling_active:
                print("[DEBUG] Superata soglia massima e deviazione standard elevata, attivazione raffreddamento.")
                print(f"[ALERT] Valori delle statistiche fuori norma: {statistics}")
                self.send_command("cooling", True)
                self.cooling_active = True
                self.heating_active = False
            self.in_range_counter = 0  # Resetta il contatore se fuori dai limiti

        # Attiva heating se la temperatura è sotto la soglia minima
        elif mean_temp < self.thresholds["min"]:
            if not self.heating_active:
                print("[DEBUG] Superata soglia minima, attivazione riscaldamento.")
                self.send_command("heating", True)
                self.heating_active = True
                self.cooling_active = False
            self.in_range_counter = 0  # Resetta il contatore se fuori dai limiti

        # La temperatura è nei limiti
        else:
            if self.cooling_active or self.heating_active:
                self.in_range_counter += 1
                print(f"[DEBUG] Temperatura nei limiti per {self.in_range_counter} rilevamenti consecutivi.")
                print(f"valore: {statistics}")
                # Disattiva gli attuatori solo dopo 3 rilevamenti consecutivi nei limiti
                if self.in_range_counter >= 3:
                    print("[DEBUG] 3 rilevamenti consecutivi nei limiti, disattivazione attuatori.")
                    self.send_command("cooling", False)
                    self.send_command("heating", False)
                    self.cooling_active = False
                    self.heating_active = False
                    self.in_range_counter = 0  # Resetta il contatore dopo disattivazione
            else:
                self.in_range_counter = 0  # Resetta se non ci sono attuatori attivi

    def send_command(self, command, activate):
        message = {
            "command": command,
            "activate": activate,
            "timestamp": time.time()
        }
        # **Construct the actuator topic dynamically**
        topic = f"{self.base_topic}/actuators/{command}"
        print(f"[DEBUG] Inviando comando: {command}, attivazione: {activate} sul topic: {topic}")
        self.mqtt_client.myPublish(topic, message)
