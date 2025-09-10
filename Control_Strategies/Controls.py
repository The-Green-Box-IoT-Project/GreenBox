import time
import logging
import statistics
import numpy as np

class BaseEnhancedControlStrategy:
    def __init__(self, thresholds, mqtt_client, base_topic, measurement_key, hysteresis_count=3, deadband=0.5):
        """
        thresholds: dizionario con soglie minime e massime (es. {"min": valore, "max": valore})
        mqtt_client: oggetto per la comunicazione MQTT
        base_topic: topic base per la pubblicazione dei comandi
        measurement_key: chiave per estrarre il dato dal record (es. "temperature", "humidity", "pH", "light", "soil_humidity")
        hysteresis_count: numero di rilevamenti consecutivi necessari per confermare la condizione
        deadband: tolleranza attorno alle soglie per evitare commutazioni troppo frequenti
        """
        self.thresholds = thresholds
        self.mqtt_client = mqtt_client
        self.base_topic = base_topic
        self.measurement_key = measurement_key
        self.hysteresis_count = hysteresis_count
        self.deadband = deadband
        self.in_range_counter = 0
        self.logger = logging.getLogger(self.__class__.__name__)
        self.logger.setLevel(logging.DEBUG)
        handler = logging.StreamHandler()
        formatter = logging.Formatter('[%(levelname)s] %(asctime)s - %(message)s')
        handler.setFormatter(formatter)
        if not self.logger.handlers:
            self.logger.addHandler(handler)
    
    def compute_statistics(self, measurements):
        values = [m[self.measurement_key] for m in measurements if self.measurement_key in m]
        if not values:
            self.logger.error("Nessun dato disponibile per il sensore %s", self.measurement_key)
            return {}
        mean_val = statistics.mean(values)
        stddev_val = statistics.stdev(values) if len(values) > 1 else 0
        return {"mean": mean_val, "stddev": stddev_val}
    
    def update(self, influx_simulator, minutes=5):
        measurements = influx_simulator.query_last_minutes(minutes)
        stats = self.compute_statistics(measurements)
        self.analyze_statistics(stats)
    
    def analyze_statistics(self, statistics):
        raise NotImplementedError("Devi implementare analyze_statistics nella sottoclasse.")
    
    def send_command(self, command, activate):
     message = {
        "command": command,
        "activate": activate,
        "timestamp": time.time()
     }
     topic = f"{self.base_topic}/actuators/{command}"
     self.logger.debug(f"Inviando comando '{command}' (attivazione: {activate}) sul topic: {topic}")
     self.mqtt_client.publish(topic, message)


# --- Strategies for temperature_sensor (Temperature) ---

class EnhancedTemperatureControlStrategy(BaseEnhancedControlStrategy):
    def __init__(self, thresholds, mqtt_client, base_topic, hysteresis_count=3, deadband=0.5):
        
        super().__init__(thresholds, mqtt_client, base_topic, measurement_key="temperature", hysteresis_count=hysteresis_count, deadband=deadband)
        self.cooling_active = False
        self.heating_active = False
    
    def analyze_statistics(self, statistics):
        mean_temp = statistics.get("mean")
        if mean_temp is None:
            self.logger.error("Missing mean temperature value")
            return
        if mean_temp > self.thresholds["max"] + self.deadband:
            if not self.cooling_active:
                self.logger.debug("High temperature: activating cooling system")
                self.send_command("cooling", True)
                self.cooling_active = True
                self.heating_active = False
            self.in_range_counter = 0
        elif mean_temp < self.thresholds["min"] - self.deadband:
            if not self.heating_active:
                self.logger.debug("Low temperature: activating heating system")
                self.send_command("heating", True)
                self.heating_active = True
                self.cooling_active = False
            self.in_range_counter = 0
        else:
            if self.cooling_active or self.heating_active:
                self.in_range_counter += 1
                self.logger.debug(f"Stable temperature for {self.in_range_counter} consecutive readings")
                if self.in_range_counter >= self.hysteresis_count:
                    self.logger.debug("Stable conditions: deactivating heating and cooling systems")
                    self.send_command("cooling", False)
                    self.send_command("heating", False)
                    self.cooling_active = False
                    self.heating_active = False
                    self.in_range_counter = 0
            else:
                self.in_range_counter = 0

class ForecastEnhancedTemperatureControlStrategy(EnhancedTemperatureControlStrategy):
    def __init__(self, thresholds, mqtt_client, base_topic, forecast_horizon=60, hysteresis_count=3, deadband=0.5):
        super().__init__(thresholds, mqtt_client, base_topic, hysteresis_count, deadband)
        self.forecast_horizon = forecast_horizon  # in seconds
    
    def forecast_future_value(self, measurements, horizon_seconds):
        times = [m["time"] for m in measurements if self.measurement_key in m]
        values = [m[self.measurement_key] for m in measurements if self.measurement_key in m]
        if len(times) < 2:
            self.logger.warning("Insufficient data for forecasting.")
            return None
        a, b = np.polyfit(times, values, 1)
        future_time = times[-1] + horizon_seconds
        forecast = a * future_time + b
        return forecast
    
    def update_and_control(self, influx_simulator, minutes=5):
        measurements = influx_simulator.query_last_minutes(minutes)
        stats = self.compute_statistics(measurements)
        self.logger.debug(f"Current Statistics: {stats}")
        forecasted_value = self.forecast_future_value(measurements, self.forecast_horizon)
        self.logger.debug(f"Forecast value for {self.forecast_horizon} seconds: {forecasted_value}")
        if forecasted_value is None:
            self.analyze_statistics(stats)
            return
        if forecasted_value > self.thresholds["max"] + self.deadband:
            if not self.cooling_active:
                self.logger.debug("Forecast indicates high temperature: activating cooling system")
                self.send_command("cooling", True)
                self.cooling_active = True
                self.heating_active = False
            self.in_range_counter = 0
        elif forecasted_value < self.thresholds["min"] - self.deadband:
            if not self.heating_active:
                self.logger.debug("Forecast indicates low temperature: activating heating system")
                self.send_command("heating", True)
                self.heating_active = True
                self.cooling_active = False
            self.in_range_counter = 0
        else:
            self.analyze_statistics(stats)


class EnhancedAirHumidityControlStrategy(BaseEnhancedControlStrategy):
    def __init__(self, thresholds, mqtt_client, base_topic, hysteresis_count=3, deadband=2):
        
        super().__init__(thresholds, mqtt_client, base_topic, measurement_key="humidity", hysteresis_count=hysteresis_count, deadband=deadband)
        self.ventilation_active = False
    
    def analyze_statistics(self, statistics):
        mean_humidity = statistics.get("mean")
        if mean_humidity is None:
            self.logger.error("Mean humidity value missing")
            return
        if mean_humidity > self.thresholds["max"] + self.deadband:
            if not self.ventilation_active:
                self.logger.debug("High humidity: activating ventilation")
                self.send_command("ventilation", True)
                self.ventilation_active = True
            self.in_range_counter = 0
        elif mean_humidity < self.thresholds["min"] - self.deadband:
            if self.ventilation_active:
                self.logger.debug("Low humidity: deactivating ventilation")
                self.send_command("ventilation", False)
                self.ventilation_active = False
            self.in_range_counter = 0
        else:
            if self.ventilation_active:
                self.in_range_counter += 1
                self.logger.debug(f"Stable humidity for {self.in_range_counter} consecutive readings")
                if self.in_range_counter >= self.hysteresis_count:
                    self.logger.debug("Stable conditions: deactivating ventilation")
                    self.send_command("ventilation", False)
                    self.ventilation_active = False
                    self.in_range_counter = 0
            else:
                self.in_range_counter = 0

class ForecastEnhancedAirHumidityControlStrategy(EnhancedAirHumidityControlStrategy):
    def __init__(self, thresholds, mqtt_client, base_topic, forecast_horizon=60, hysteresis_count=3, deadband=2):
        super().__init__(thresholds, mqtt_client, base_topic, hysteresis_count, deadband)
        self.forecast_horizon = forecast_horizon
    
    def forecast_future_value(self, measurements, horizon_seconds):
        times = [m["time"] for m in measurements if self.measurement_key in m]
        values = [m[self.measurement_key] for m in measurements if self.measurement_key in m]
        if len(times) < 2:
            self.logger.warning("Insufficient data for forecasting.")
            return None
        a, b = np.polyfit(times, values, 1)
        future_time = times[-1] + horizon_seconds
        forecast = a * future_time + b
        return forecast
    
    def update_and_control(self, influx_simulator, minutes=5):
        measurements = influx_simulator.query_last_minutes(minutes)
        stats = self.compute_statistics(measurements)
        self.logger.debug(f"Current Statistics: {stats}")
        forecasted_value = self.forecast_future_value(measurements, self.forecast_horizon)
        self.logger.debug(f"Forecast value for {self.forecast_horizon} seconds: {forecasted_value}")
        if forecasted_value is None:
            self.analyze_statistics(stats)
            return
        if forecasted_value > self.thresholds["max"] + self.deadband:
            if not self.ventilation_active:
                self.logger.debug("Forecast indicates high humidity: activating ventilation")
                self.send_command("ventilation", True)
                self.ventilation_active = True
            self.in_range_counter = 0
        elif forecasted_value < self.thresholds["min"] - self.deadband:
            if self.ventilation_active:
                self.logger.debug("Forecast indicates low humidity: deactivating ventilation")
                self.send_command("ventilation", False)
                self.ventilation_active = False
            self.in_range_counter = 0
        else:
            self.analyze_statistics(stats)


# --- Strategies per ph_meter (pH) ---

class EnhancedPHControlStrategy(BaseEnhancedControlStrategy):
    def __init__(self, thresholds, mqtt_client, base_topic, hysteresis_count=3, deadband=0.2):
        # I dati di pH vengono attesi con la chiave "pH"
        super().__init__(thresholds, mqtt_client, base_topic, measurement_key="pH", hysteresis_count=hysteresis_count, deadband=deadband)
        self.adjustment_active = False
    
    def analyze_statistics(self, statistics):
        mean_ph = statistics.get("mean")
        if mean_ph is None:
            self.logger.error("Mean pH value missing")
            return
        if mean_ph < self.thresholds["min"] - self.deadband:
            if not self.adjustment_active:
                self.logger.debug("Low pH: activating pH regulation (base addition)")
                self.send_command("pH_adjust", True)
                self.adjustment_active = True
            self.in_range_counter = 0
        elif mean_ph > self.thresholds["max"] + self.deadband:
            if not self.adjustment_active:
                self.logger.debug("High pH: activating pH regulation (acid addition)")
                self.send_command("pH_adjust", True)
                self.adjustment_active = True
            self.in_range_counter = 0
        else:
            if self.adjustment_active:
                self.in_range_counter += 1
                self.logger.debug(f"Stable pH for {self.in_range_counter} consecutive readings")
                if self.in_range_counter >= self.hysteresis_count:
                    self.logger.debug("Stable conditions: deactivating pH regulation")
                    self.send_command("pH_adjust", False)
                    self.adjustment_active = False
                    self.in_range_counter = 0
            else:
                self.in_range_counter = 0

class ForecastEnhancedPHControlStrategy(EnhancedPHControlStrategy):
    def __init__(self, thresholds, mqtt_client, base_topic, forecast_horizon=60, hysteresis_count=3, deadband=0.2):
        super().__init__(thresholds, mqtt_client, base_topic, hysteresis_count, deadband)
        self.forecast_horizon = forecast_horizon
    
    def forecast_future_value(self, measurements, horizon_seconds):
        times = [m["time"] for m in measurements if self.measurement_key in m]
        values = [m[self.measurement_key] for m in measurements if self.measurement_key in m]
        if len(times) < 2:
            self.logger.warning("Insufficient data for forecasting.")
            return None
        a, b = np.polyfit(times, values, 1)
        future_time = times[-1] + horizon_seconds
        forecast = a * future_time + b
        return forecast
    
    def update_and_control(self, influx_simulator, minutes=5):
        measurements = influx_simulator.query_last_minutes(minutes)
        stats = self.compute_statistics(measurements)
        self.logger.debug(f"Current Statistics: {stats}")
        forecasted_value = self.forecast_future_value(measurements, self.forecast_horizon)
        self.logger.debug(f"Forecast value for {self.forecast_horizon} seconds: {forecasted_value}")
        if forecasted_value is None:
            self.analyze_statistics(stats)
            return
        if forecasted_value < self.thresholds["min"] - self.deadband or forecasted_value > self.thresholds["max"] + self.deadband:
            if not self.adjustment_active:
                self.logger.debug("Forecast indicates pH out of range: activating pH regulation")
                self.send_command("pH_adjust", True)
                self.adjustment_active = True
            self.in_range_counter = 0
        else:
            self.analyze_statistics(stats)


# --- Strategies per PAR_meter---

class EnhancedIlluminationControlStrategy(BaseEnhancedControlStrategy):
    def __init__(self, thresholds, mqtt_client, base_topic, hysteresis_count=3, deadband=10):
        
        super().__init__(thresholds, mqtt_client, base_topic, measurement_key="light", hysteresis_count=hysteresis_count, deadband=deadband)
        self.illumination_active = False
    
    def analyze_statistics(self, statistics):
        mean_light = statistics.get("mean")
        if mean_light is None:
            self.logger.error("Mean light value missing")
            return
        if mean_light < self.thresholds["min"] - self.deadband:
            if not self.illumination_active:
                self.logger.debug("Low light: activating lamp")
                self.send_command("illumination", True)
                self.illumination_active = True
            self.in_range_counter = 0
        elif mean_light > self.thresholds["max"] + self.deadband:
            if self.illumination_active:
                self.logger.debug("High light: deactivating lamp")
                self.send_command("illumination", False)
                self.illumination_active = False
            self.in_range_counter = 0
        else:
            if self.illumination_active:
                self.in_range_counter += 1
                self.logger.debug(f"Stable light for {self.in_range_counter} consecutive readings")
                if self.in_range_counter >= self.hysteresis_count:
                    self.logger.debug("Stable conditions: deactivating lamp")
                    self.send_command("illumination", False)
                    self.illumination_active = False
                    self.in_range_counter = 0
            else:
                self.in_range_counter = 0

class ForecastEnhancedIlluminationControlStrategy(EnhancedIlluminationControlStrategy):
    def __init__(self, thresholds, mqtt_client, base_topic, forecast_horizon=60, hysteresis_count=3, deadband=10):
        super().__init__(thresholds, mqtt_client, base_topic, hysteresis_count, deadband)
        self.forecast_horizon = forecast_horizon
    
    def forecast_future_value(self, measurements, horizon_seconds):
        times = [m["time"] for m in measurements if self.measurement_key in m]
        values = [m[self.measurement_key] for m in measurements if self.measurement_key in m]
        if len(times) < 2:
            self.logger.warning("Insufficient data for forecasting.")
            return None
        a, b = np.polyfit(times, values, 1)
        future_time = times[-1] + horizon_seconds
        forecast = a * future_time + b
        return forecast

    def update_and_control(self, influx_simulator, minutes=5):
        measurements = influx_simulator.query_last_minutes(minutes)
        stats = self.compute_statistics(measurements)
        self.logger.debug(f"Current Statistics: {stats}")
        forecasted_value = self.forecast_future_value(measurements, self.forecast_horizon)
        self.logger.debug(f"Forecast value for {self.forecast_horizon} seconds: {forecasted_value}")
        if forecasted_value is None:
            self.analyze_statistics(stats)
            return
        if forecasted_value < self.thresholds["min"] - self.deadband:
            if not self.illumination_active:
                self.logger.debug("Forecast indica illuminazione bassa: attivazione lampada")
                self.send_command("illumination", True)
                self.illumination_active = True
            self.in_range_counter = 0
        elif forecasted_value > self.thresholds["max"] + self.deadband:
            if self.illumination_active:
                self.logger.debug("Forecast indicates high light: deactivating lamp")
                self.send_command("illumination", False)
                self.illumination_active = False
            self.in_range_counter = 0
        else:
            self.analyze_statistics(stats)


# --- Strategies per soil_hygrometer (Soil humidity) ---

class EnhancedSoilHumidityControlStrategy(BaseEnhancedControlStrategy):
    def __init__(self, thresholds, mqtt_client, base_topic, hysteresis_count=3, deadband=5):
        
        super().__init__(thresholds, mqtt_client, base_topic, measurement_key="soil_humidity", hysteresis_count=hysteresis_count, deadband=deadband)
        self.irrigation_active = False
    
    def analyze_statistics(self, statistics):
        mean_soil_humidity = statistics.get("mean")
        if mean_soil_humidity is None:
            self.logger.error("Mean soil humidity value missing")
            return
        if mean_soil_humidity < self.thresholds["min"] - self.deadband:
            if not self.irrigation_active:
                self.logger.debug("Low soil humidity: activating irrigation")
                self.send_command("irrigation", True)
                self.irrigation_active = True
            self.in_range_counter = 0
        elif mean_soil_humidity > self.thresholds["max"] + self.deadband:
            if self.irrigation_active:
                self.logger.debug("High soil humidity: deactivating irrigation")
                self.send_command("irrigation", False)
                self.irrigation_active = False
            self.in_range_counter = 0
        else:
            if self.irrigation_active:
                self.in_range_counter += 1
                self.logger.debug(f"Stable soil humidity for {self.in_range_counter} consecutive readings")
                if self.in_range_counter >= self.hysteresis_count:
                    self.logger.debug("Stable conditions: deactivating irrigation")
                    self.send_command("irrigation", False)
                    self.irrigation_active = False
                    self.in_range_counter = 0
            else:
                self.in_range_counter = 0

class ForecastEnhancedSoilHumidityControlStrategy(EnhancedSoilHumidityControlStrategy):
    def __init__(self, thresholds, mqtt_client, base_topic, forecast_horizon=60, hysteresis_count=3, deadband=5):
        super().__init__(thresholds, mqtt_client, base_topic, hysteresis_count, deadband)
        self.forecast_horizon = forecast_horizon
    
    def forecast_future_value(self, measurements, horizon_seconds):
        times = [m["time"] for m in measurements if self.measurement_key in m]
        values = [m[self.measurement_key] for m in measurements if self.measurement_key in m]
        if len(times) < 2:
            self.logger.warning("Insufficient data for forecasting.")
            return None
        a, b = np.polyfit(times, values, 1)
        future_time = times[-1] + horizon_seconds
        forecast = a * future_time + b
        return forecast
    
    def update_and_control(self, influx_simulator, minutes=5):
        measurements = influx_simulator.query_last_minutes(minutes)
        stats = self.compute_statistics(measurements)
        self.logger.debug(f"Current Statistics: {stats}")
        forecasted_value = self.forecast_future_value(measurements, self.forecast_horizon)
        self.logger.debug(f"Forecast value for {self.forecast_horizon} seconds: {forecasted_value}")
        if forecasted_value is None:
            self.analyze_statistics(stats)
            return
        if forecasted_value < self.thresholds["min"] - self.deadband:
            if not self.irrigation_active:
                self.logger.debug("Forecast indicates low soil humidity: activating irrigation")
                self.send_command("irrigation", True)
                self.irrigation_active = True
            self.in_range_counter = 0
        elif forecasted_value > self.thresholds["max"] + self.deadband:
            if self.irrigation_active:
                self.logger.debug("Forecast indicates high soil humidity: deactivating irrigation")
                self.send_command("irrigation", False)
                self.irrigation_active = False
            self.in_range_counter = 0
        else:
            self.analyze_statistics(stats)
