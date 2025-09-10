import json
from control_strategies import BasicControlStrategy, AdvancedControlStrategy

class ControlModule:
    def __init__(self, mqtt_client, raspberry_id, base_topic):
        self.mqtt_client = mqtt_client
        self.base_topic = base_topic
        # Carica la strategia specifica per il Raspberry Pi corrente
        self.strategy = self.load_strategy(raspberry_id)

    def load_strategy(self, raspberry_id):
        # Carica il file strategies.json unificato
        with open("strategies.json") as f:
            strategies = json.load(f)

        # Trova la configurazione del client basata sull'ID del Raspberry Pi
        for client in strategies["clients"]:
            if client["raspberry_id"] == raspberry_id:
                strategy_name = client["control_strategy"]
                print(f"[DEBUG] Strategia caricata: {strategy_name}")

                # Carica le soglie per ciascun attuatore dal nuovo file unificato
                thresholds = {}
                for actuator in client.get("actuators", []):
                    actuator_name = actuator["name"]
                    thresholds[actuator_name] = {
                        "thresholds": actuator.get("thresholds", {}),
                        "activation": actuator.get("activation", False),
                        "deactivation_counter": actuator.get("deactivation_counter", 0)
                    }

                print(f"[DEBUG] Soglie caricate per gli attuatori con deactivation_counter: {thresholds}")

                # Seleziona e ritorna la strategia corretta con le soglie caricate
                if strategy_name == "BasicControlStrategy":
                    print("[DEBUG] Caricamento BasicControlStrategy")
                    return BasicControlStrategy(client, thresholds, self.mqtt_client, self.base_topic)
                elif strategy_name == "AdvancedControlStrategy":
                    print("[DEBUG] Caricamento AdvancedControlStrategy")
                    return AdvancedControlStrategy(client, thresholds, self.mqtt_client, self.base_topic)
                else:
                    raise ValueError(f"Strategia sconosciuta: {strategy_name}")

        # Solleva un'eccezione se il Raspberry Pi non è trovato nel file strategies.json
        raise ValueError("Raspberry Pi non trovato nel file strategies.json.")

    def analyze_statistics(self, statistics):
        """
        Invia le statistiche alla strategia caricata per decidere le azioni.
        """
        print(f"[DEBUG] Statistiche ricevute: {statistics}")
        self.strategy.analyze_statistics(statistics)
