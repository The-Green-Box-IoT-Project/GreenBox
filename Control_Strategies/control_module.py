import json
from control_strategies import BasicControlStrategy, AdvancedControlStrategy


class ControlModule:
    def __init__(self, mqtt_client, raspberry_id, base_topic):
        self.mqtt_client = mqtt_client
        self.base_topic = base_topic
        # Load the specific strategy for the current Raspberry Pi
        self.strategy = self.load_strategy(raspberry_id)

    def load_strategy(self, raspberry_id):
        with open("catalog.json") as f:
            catalog = json.load(f)

        for client in catalog["clients"]:
            if client["raspberry_id"] == raspberry_id:
                strategy_name = client["control_strategy"]
                print(f"[DEBUG] Strategia caricata: {strategy_name}")

                thresholds = {"min": 18.0, "max": 24.0}
                if strategy_name == "BasicControlStrategy":
                    print("[DEBUG] Caricamento BasicControlStrategy")
                    return BasicControlStrategy(thresholds, self.mqtt_client, self.base_topic)
                elif strategy_name == "AdvancedControlStrategy":
                    print("[DEBUG] Caricamento AdvancedControlStrategy")
                    return AdvancedControlStrategy(thresholds, self.mqtt_client, self.base_topic)
                else:
                    raise ValueError(f"Strategia sconosciuta: {strategy_name}")

        raise ValueError("Raspberry Pi non trovato nel catalogo.")

    def analyze_statistics(self, statistics):
        """
        Forward statistics to the loaded strategy to decide actions.
        """
        self.strategy.analyze_statistics(statistics)
