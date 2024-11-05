import json
import statistics as stats  # Usa il modulo statistics standard
import numpy as np
from scipy import stats as scipy_stats  # Rinomina scipy.stats per evitare conflitti
import ijson


def load_historical_data_in_chunks(historical_file):
    """Carica i dati storici a blocchi usando ijson."""
    with open(historical_file, 'r') as file:
        for item in ijson.items(file, 'item'):
            yield item  # Restituisce un oggetto alla volta


def compare_with_historical_in_chunks(historical_file, current_stats, current_variance, current_slope,
                                      cleaned_temperatures):
    """Confronta i dati attuali con i dati storici caricati a blocchi."""
    historical_mean = 0
    historical_min = float('inf')
    historical_max = float('-inf')
    historical_temperatures = []
    count = 0

    for historical_entry in load_historical_data_in_chunks(historical_file):
        historical_temp = float(historical_entry['temperature'])
        historical_temperatures.append(historical_temp)
        historical_mean += historical_temp
        historical_min = min(historical_min, historical_temp)
        historical_max = max(historical_max, historical_temp)
        count += 1

    if count > 0:
        historical_mean /= count  # Calcola la media storica
        historical_stddev = np.std(historical_temperatures) if count > 1 else 0
        historical_variance = np.var(historical_temperatures) if count > 1 else 0
        historical_slope = linear_trend(historical_temperatures)  # Calcola il trend storico

        comparison = {
            "mean_difference": current_stats['mean'] - historical_mean,
            "min_difference": current_stats['min'] - historical_min,
            "max_difference": current_stats['max'] - historical_max,
            "stddev_difference": current_stats["stddev"] - historical_stddev,
            "variance_difference": current_variance - historical_variance,
            "trend_difference": current_slope - historical_slope
        }

        # Confronto con la media mobile
        smoothed_historical_temperatures = moving_average(historical_temperatures, window_size=5)
        smoothed_historical_temperatures = [temp for temp in smoothed_historical_temperatures if temp is not None]

        smoothed_current_temperatures = moving_average(cleaned_temperatures, window_size=5)
        smoothed_current_temperatures = [temp for temp in smoothed_current_temperatures if temp is not None]

        if smoothed_historical_temperatures and smoothed_current_temperatures:
            comparison["smoothed_mean_difference"] = np.mean(smoothed_current_temperatures) - np.mean(
                smoothed_historical_temperatures)

        return comparison
    else:
        return None


def moving_average(data, window_size):
    """Calcola la media mobile per una serie di dati."""
    return np.convolve(data, np.ones(window_size) / window_size, mode='valid')


def remove_outliers(data):
    """Rimuove gli outlier dai dati utilizzando l'IQR."""
    q1 = np.percentile(data, 25)
    q3 = np.percentile(data, 75)
    iqr = q3 - q1
    lower_bound = q1 - 1.5 * iqr
    upper_bound = q3 + 1.5 * iqr
    return [x for x in data if lower_bound <= x <= upper_bound]


def calculate_variance_stddev(data):
    """Calcola la varianza e la deviazione standard dei dati."""
    if len(data) > 1:
        variance = stats.variance(data)
        stddev = stats.stdev(data)
    else:
        variance = 0
        stddev = 0
    return variance, stddev


def linear_trend(temperature_data):
    """Calcola il trend lineare di una serie temporale."""
    x = np.arange(len(temperature_data))  # Indici temporali
    slope, _, _, _, _ = scipy_stats.linregress(x, temperature_data)
    return slope


def calculate_statistics(data):
    """Calcola media, min, max e deviazione standard."""
    if not data:
        return None

    mean_value = np.mean(data)
    min_value = np.min(data)
    max_value = np.max(data)
    stddev_value = np.std(data) if len(data) > 1 else 0

    return {
        "mean": mean_value,
        "min": min_value,
        "max": max_value,
        "stddev": stddev_value
    }
