import os
import threading
import time
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Any
import pandas as pd
from utils.mqtt import MyMQTT
from utils.client import get_all_stats_zones, get_measurements, get_readings


class StateAggregator:
    """
    A timed aggregator that periodically fetches the complete state for each
    greenhouse/raspberry zone, calculates statistics, and publishes a single
    snapshot message for each zone.
    """

    def __init__(self):
        # Load broker from environment TODO: secondo me va aggiunto a mongo
        self.broker_ip = os.environ.get("BROKER_IP")
        self.broker_port = int(os.environ.get("BROKER_PORT"))

        # MQTT client for publishing
        self.mqtt = MyMQTT(clientID="statistics_aggregator", broker=self.broker_ip, port=self.broker_port, notifier=None)

        # Timing configuration from environment variables
        self.window_minutes = int(os.environ.get("STATS_WINDOW_MINUTES", "5"))
        self.aggregation_interval_s = int(os.environ.get("STATS_AGGREGATION_INTERVAL_S", "10"))

        # Threading control
        self._stop_event = threading.Event()
        self._thread = None

    def start(self):
        """Start the aggregator loop in a separate thread."""
        print("Starting StateAggregator...")
        self.mqtt.start()
        self._thread = threading.Thread(target=self.run, daemon=True)
        self._thread.start()
        print(f"StateAggregator started. Aggregation interval: {self.aggregation_interval_s} seconds.")

    def stop(self):
        """Signal the aggregator loop to stop gracefully."""
        print("Stopping StateAggregator...")
        self._stop_event.set()
        if self._thread and self._thread.is_alive():
            self._thread.join()  # Wait for the thread to finish
        self.mqtt.stop()
        print("StateAggregator stopped.")

    def run(self):
        """The main loop of the aggregator service."""
        while not self._stop_event.is_set():
            print("Starting aggregation cycle...")
            
            start_time = time.time()

            # 1. Recupera la lista delle misurazioni (resiliente se il DB è giù)
            self.measurements = get_measurements()
            
            # 2. Recupera le zone (resiliente)
            zones = get_all_stats_zones()
            
            if not self.measurements:
                print("[WARNING] Nessuna metrica definita o DB non raggiungibile. Salto il ciclo.")
            elif not zones:
                print("[WARNING] Nessuna zona definita o DB non raggiungibile. Salto il ciclo.")
            else:
                print("Zones received: %s", zones)
                for z in zones:
                    gh_id = z["greenhouse_id"]
                    rb_id = z["raspberry_id"]
                    self._process_zone(gh_id, rb_id, self.measurements)

            cycle_duration = time.time() - start_time
            print(f"Aggregation cycle finished in {cycle_duration:.2f} seconds.")

            # Wait for the next cycle
            sleep_time = max(0, self.aggregation_interval_s - cycle_duration)
            self._stop_event.wait(timeout=sleep_time)

    def _process_zone(self, gh_id: str, rb_id: str, measurements: List[str]):
        """Fetch, aggregate, and publish the state for a single zone."""
        print(f"[{gh_id}/{rb_id}] Processing zone...")
        
        aggregated_metrics = self._fetch_and_aggregate_metrics(gh_id, rb_id, measurements)
        
        if not aggregated_metrics:
            print(f"[{gh_id}/{rb_id}] No metrics to publish.")
            return

        self._publish_zone_state(gh_id, rb_id, aggregated_metrics)

    def _fetch_and_aggregate_metrics(self, gh_id: str, rb_id: str, measurements: List[str]) -> Dict[str, Any]:
        """Query InfluxDB for all metrics and calculate the median for each."""
        
        # Usa datetime.now(timezone.utc) è più moderno e sicuro di utcnow().replace
        end_ts = datetime.now(timezone.utc)
        start_ts = end_ts - timedelta(minutes=self.window_minutes)
        
        metrics_data = {}
        
        for metric in measurements:
            # FIX 1: Forziamo la Z al posto di +00:00 per compatibilità con InfluxDB/Arrow
            start_str = start_ts.isoformat().replace("+00:00", "Z")
            end_str = end_ts.isoformat().replace("+00:00", "Z")

            data = get_readings(
                metric=metric,
                device=rb_id,
                start=start_str,
                end=end_str,
            )

            if not data:
                continue

            try:
                # FIX 2: I dati grezzi sono una lista di liste [[time, val], ...].
                # Pandas assegna colonne 0 e 1 di default. Dobbiamo nominarle.
                df = pd.DataFrame(data, columns=["time", "value"])
                
                if "value" in df and not df["value"].empty:
                    median_value = float(df["value"].astype(float).median()) 
                    metrics_data[metric] = {"median": round(median_value, 3)}
                    
            except Exception as e:
                # Ho aggiunto %s nell'interpolazione che mancava nel print originale se usi logging standard
                print(f"[{gh_id}/{rb_id}] Failed to process data for metric '{metric}': {e}")
        
        return metrics_data

    def _publish_zone_state(self, gh_id: str, rb_id: str, aggregated_metrics: Dict[str, Any]):
        """Construct the full JSON payload and publish it to MQTT."""
        topic = f"/{gh_id}/{rb_id}/statistics/state"
        
        payload = {
            "timestamp_utc": datetime.utcnow().replace(tzinfo=timezone.utc).isoformat(),
            "greenhouse_id": gh_id,
            "raspberry_id": rb_id,
            "metrics": aggregated_metrics
        }
        
        self.mqtt.MyPublish(topic, payload)
        print(f"[{gh_id}/{rb_id}] Payload: {payload}")
