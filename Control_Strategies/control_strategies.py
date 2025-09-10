import json


class BasicControlStrategy:
    def __init__(self, client, thresholds, mqtt_client, base_topic):
        self.client = client
        self.thresholds = thresholds
        self.mqtt_client = mqtt_client
        self.base_topic = base_topic
        self.counters = {actuator: 0 for actuator in thresholds.keys()}
        self.activation_states = {actuator: False for actuator in thresholds.keys()}  # Stato attuale di attivazione

    def analyze_statistics(self, statistics):
        for actuator, params in self.thresholds.items():
            if self.values_out_of_threshold(statistics, params["thresholds"]):
                # Attiva l'attuatore se fuori soglia e resetta il contatore
                if not self.activation_states[actuator]:  # Attiva solo se non è già attivo
                    self.activate_actuator(actuator)
                    self.activation_states[actuator] = True
                self.counters[actuator] = 0  # Resetta il contatore ogni volta che è fuori soglia
                print(f"[DEBUG] Contatore per {actuator} resettato a 0 (attivazione)")
            else:
                # Incrementa il contatore se i valori sono nelle soglie e l'attuatore è attivo
                if self.activation_states[actuator]:
                    self.counters[actuator] += 1
                    print(
                        f"[DEBUG] Contatore per {actuator}: {self.counters[actuator]}/{params['deactivation_counter']}")

                    # Disattiva solo se il contatore raggiunge il deactivation_counter
                    if self.counters[actuator] >= params["deactivation_counter"]:
                        self.deactivate_actuator(actuator)
                        self.activation_states[actuator] = False
                        self.counters[actuator] = 0  # Resetta il contatore dopo la disattivazione
                        print(f"[DEBUG] Contatore per {actuator} resettato a 0 (disattivazione)")

    def activate_actuator(self, actuator):
        topic = f"{self.base_topic}/{actuator}/control"
        message = {"activation": True}
        print(f"[INFO] Attivazione attuatore {actuator}")
        self.mqtt_client.myPublish(topic, message)
        self.update_catalog_file(actuator, True)

    def deactivate_actuator(self, actuator):
        topic = f"{self.base_topic}/{actuator}/control"
        message = {"activation": False}
        print(f"[INFO] Disattivazione attuatore {actuator}")
        self.mqtt_client.myPublish(topic, message)
        self.update_catalog_file(actuator, False)

    def update_catalog_file(self, actuator_name, state):
        """
        Aggiorna lo stato di attivazione dell'attuatore nel file strategies.json.
        """
        try:
            # Carica il contenuto corrente del file
            with open("strategies.json", "r") as file:
                strategies = json.load(file)

            # Trova la configurazione del client basata su raspberry_id o client_name
            for client in strategies["clients"]:
                if client["raspberry_id"] == self.client["raspberry_id"]:
                    # Trova la configurazione dell'attuatore e aggiorna il campo 'activation'
                    for actuator in client.get("actuators", []):
                        if actuator["name"] == actuator_name:
                            actuator["activation"] = state
                            break
                    break

            # Salva il file aggiornato
            with open("strategies.json", "w") as file:
                json.dump(strategies, file, indent=4)
            print(f"[INFO] Stato di '{actuator_name}' aggiornato a '{state}' nel file strategies.json")

        except Exception as e:
            print(f"[ERROR] Errore nell'aggiornamento del file strategies.json: {e}")

    def values_out_of_threshold(self, statistics, thresholds):
        """
        Verifica se le statistiche sono fuori dai limiti di soglia definiti.
        """
        for metric, threshold in thresholds.items():
            mean_value = statistics.get(f"mean_{metric}")
            stddev_value = statistics.get(f"stddev_{metric}")
            # Controlla i valori della deviazione standard
            if stddev_value is not None:
                if "stddev_max" in threshold and stddev_value > threshold["stddev_max"]:
                    print(f"[DEBUG] stddev_{metric} = {stddev_value} supera stddev_max = {threshold['stddev_max']}")
                    return True
            # Controlla i valori medi
            if mean_value is not None:
                if "min" in threshold and mean_value < threshold["min"]:
                    print(f"[DEBUG] mean_{metric} = {mean_value} è inferiore a min = {threshold['min']}")
                    return True
                if "max" in threshold and mean_value > threshold["max"]:
                    print(f"[DEBUG] mean_{metric} = {mean_value} è superiore a max = {threshold['max']}")
                    return True
        return False


class AdvancedControlStrategy(BasicControlStrategy):
    """
    La strategia avanzata estende la strategia di base aggiungendo il monitoraggio della deviazione standard e della pendenza del trend.
    """

    def values_out_of_threshold(self, statistics, thresholds):
        for metric, threshold in thresholds.items():
            mean_value = statistics.get(f"mean_{metric}")
            stddev_value = statistics.get(f"stddev_{metric}")
            slope_value = statistics.get(f"slope_{metric}")

            # Controlla i valori medi
            if mean_value is not None:
                if "min" in threshold and mean_value < threshold["min"]:
                    print(f"[DEBUG] {metric} = {mean_value} è inferiore a min = {threshold['min']}")
                    return True
                if "max" in threshold and mean_value > threshold["max"]:
                    print(f"[DEBUG] {metric} = {mean_value} è superiore a max = {threshold['max']}")
                    return True

            # Controlla la deviazione standard
            if stddev_value is not None and "stddev_max" in threshold:
                if stddev_value > threshold["stddev_max"]:
                    print(f"[DEBUG] stddev_{metric} = {stddev_value} supera stddev_max = {threshold['stddev_max']}")
                    return True

            # Controlla la pendenza del trend
            if slope_value is not None and "slope_threshold" in threshold:
                if abs(slope_value) > threshold["slope_threshold"]:
                    print(
                        f"[DEBUG] slope_{metric} = {slope_value} supera slope_threshold = {threshold['slope_threshold']}")
                    return True

        return False
