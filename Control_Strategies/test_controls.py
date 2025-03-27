import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from utils.tools import (convert_str_to_datetime, read_env, mock_values_mapper, Today,
                   get_latest_entry_before_now, convert_df_to_list, extend_time_interval)
from utils.generate_mock_time_series import MockTimeSeriesWrapper


from InfluxDB_Adapter.db_simulator import InfluxDBSimulator
from Control_Strategies.Controls import (
    ForecastEnhancedTemperatureControlStrategy,
    ForecastEnhancedAirHumidityControlStrategy,
    ForecastEnhancedPHControlStrategy,
    ForecastEnhancedIlluminationControlStrategy,
    ForecastEnhancedSoilHumidityControlStrategy)

import json
from Control_Strategies.myMQTT import MyMQTT



# Map the strategy names to the corresponding classes
strategy_mapping = {
    "ForecastEnhancedTemperatureControlStrategy": ForecastEnhancedTemperatureControlStrategy,
    "ForecastEnhancedAirHumidityControlStrategy": ForecastEnhancedAirHumidityControlStrategy,
    "ForecastEnhancedPHControlStrategy": ForecastEnhancedPHControlStrategy,
    "ForecastEnhancedIlluminationControlStrategy": ForecastEnhancedIlluminationControlStrategy,
    "ForecastEnhancedSoilHumidityControlStrategy": ForecastEnhancedSoilHumidityControlStrategy
}

def main():
    # Load the catalog and configuration files
    catalog_path = "Control_Strategies\catalog.json"
    config_path = "Control_Strategies\confg.json"
    if not os.path.exists(catalog_path) or os.path.getsize(catalog_path) == 0:
        print(f"Error: {catalog_path} does not exist or is empty.")
        return
    
    with open(catalog_path, "r") as f:
        catalog = json.load(f)
    broker = "localhost"
    port = 1883
    clientID = "RaspberryConnector"
    
    
    mqtt_client = MyMQTT(broker, port, clientID,notifier=None)
    mqtt_client.connect()
    
    
    for metric, config in catalog.items():
        print(f"Processing metric: {metric}")
        
        mock_file = config.get("mock_file")
        base_topic = config.get("base_topic")
        strategy_name = config.get("strategy")
        thresholds = config.get("thresholds")
        
        if not (mock_file and base_topic and strategy_name and thresholds):
            print(f"Missing configuration for metric: {metric}, skipping.")
            continue
        
        mock_file_path = os.path.join(os.getcwd(), mock_file)
        
        # Instantiate the simulator for this metric
        simulator = InfluxDBSimulator(mock_file_path, metric)
        
        # Obtain the strategy class for this metric
        strategy_class = strategy_mapping.get(strategy_name)
        if strategy_class is None:
            print(f"Not a valid strategy: {strategy_name}, skipping.")
            continue
        
        # Extract the thresholds for this metric
        forecast_horizon = thresholds.get("forecast_horizon", 60)
        hysteresis_count = thresholds.get("hysteresis_count", 3)
        deadband = thresholds.get("deadband", 0.5)
        
        # Instantiate the strategy
        strategy = strategy_class(thresholds, mqtt_client, base_topic,
                                  forecast_horizon=forecast_horizon,
                                  hysteresis_count=hysteresis_count,
                                  deadband=deadband)
        
        # Update and control the simulator for 5 minutes
        strategy.update_and_control(simulator, minutes=5)
    
if __name__ == "__main__":
    
    main()
