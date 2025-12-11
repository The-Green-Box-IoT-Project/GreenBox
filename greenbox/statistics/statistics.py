import logging
import os
import threading
import time
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Any

import pandas as pd
from greenbox.utils import catalog_client
from greenbox.utils.mqtt import MyMQTT
from greenbox.utils.influx_client import InfluxInterfaceClient


class StateAggregator:
    """
    A timed aggregator that periodically fetches the complete state for each
    greenhouse/raspberry zone, calculates statistics, and publishes a single
    snapshot message for each zone.
    """

    def __init__(self):
        # Load configuration from catalog using the new specific function
        catalog_data = catalog_client.get_all_zones_with_measurements()
        self.broker_ip = catalog_data["broker_ip"]
        self.broker_port = catalog_data["broker_port"]
        self.greenhouses_config = catalog_data["greenhouses"]

        # MQTT client for publishing
        self.mqtt = MyMQTT(clientID="statistics_aggregator", broker=self.broker_ip, port=self.broker_port, notifier=None)
        
        # InfluxDB client for querying data
        self.influx_client = InfluxInterfaceClient()

        # Timing configuration from environment variables
        self.window_minutes = int(os.getenv("STATS_WINDOW_MINUTES", "5"))
        self.aggregation_interval_s = int(os.getenv("STATS_AGGREGATION_INTERVAL_S", "10"))

        # Threading control
        self._stop_event = threading.Event()
        self._thread = None

    def start(self):
        """Start the aggregator loop in a separate thread."""
        logging.info("Starting StateAggregator...")
        self.mqtt.start()
        self._thread = threading.Thread(target=self.run, daemon=True)
        self._thread.start()
        logging.info("StateAggregator started. Aggregation interval: %d seconds.", self.aggregation_interval_s)

    def stop(self):
        """Signal the aggregator loop to stop gracefully."""
        logging.info("Stopping StateAggregator...")
        self._stop_event.set()
        if self._thread and self._thread.is_alive():
            self._thread.join()  # Wait for the thread to finish
        self.mqtt.stop()
        logging.info("StateAggregator stopped.")

    def run(self):
        """The main loop of the aggregator service."""
        while not self._stop_event.is_set():
            logging.info("Starting aggregation cycle...")
            
            start_time = time.time()

            for gh_config in self.greenhouses_config:
                gh_id = gh_config["greenhouse_id"]
                measurements = gh_config["measurements"]
                
                for rb_id in gh_config["raspberries"]:
                    try:
                        self._process_zone(gh_id, rb_id, measurements)
                    except Exception as e:
                        logging.error("[%s/%s] Failed to process zone: %s", gh_id, rb_id, e, exc_info=True)

            cycle_duration = time.time() - start_time
            logging.info("Aggregation cycle finished in %.2f seconds.", cycle_duration)

            # Wait for the next cycle, accounting for processing time
            sleep_time = max(0, self.aggregation_interval_s - cycle_duration)
            self._stop_event.wait(timeout=sleep_time)

    def _process_zone(self, gh_id: str, rb_id: str, measurements: List[str]):
        """Fetch, aggregate, and publish the state for a single zone."""
        logging.debug("[%s/%s] Processing zone...", gh_id, rb_id)
        
        aggregated_metrics = self._fetch_and_aggregate_metrics(gh_id, rb_id, measurements)
        
        if not aggregated_metrics:
            return

        self._publish_zone_state(gh_id, rb_id, aggregated_metrics)

    def _fetch_and_aggregate_metrics(self, gh_id: str, rb_id: str, measurements: List[str]) -> Dict[str, Any]:
        """Query InfluxDB for all metrics and calculate the median for each."""
        end_ts = datetime.utcnow().replace(tzinfo=timezone.utc)
        start_ts = end_ts - timedelta(minutes=self.window_minutes)
        
        metrics_data = {}
        
        for metric in measurements:
            # Query InfluxDB for a single metric
            data = self.influx_client.get_data(
                metric=metric,
                start=start_ts.isoformat(),
                end=end_ts.isoformat(),
                site=gh_id,
                device=rb_id,
                limit=10_000,
            )

            if not data:
                continue

            try:
                df = pd.DataFrame(data)
                if "value" in df and not df["value"].empty:
                    median_value = float(df["value"].astype(float).median()) # Explicit cast to float
                    metrics_data[metric] = {"median": round(median_value, 3)}
            except Exception as e:
                logging.error("[%s/%s] Failed to process data for metric '%s': %s", gh_id, rb_id, metric, e)
        
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
        logging.debug("[%s/%s] Payload: %s", gh_id, rb_id, payload)