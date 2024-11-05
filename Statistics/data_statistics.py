import statistics as stats  # Usa il modulo statistics standard
import numpy as np
from scipy import stats as scipy_stats  # Rinomina scipy.stats per evitare conflitti


def moving_average(data, window_size):
    """Calcola la media mobile per una serie di dati."""
    return np.convolve(data, np.ones(window_size) / window_size, mode='valid')


def remove_outliers(data):
    """Rimuove gli outlier dai dati utilizzando l'IQR."""
    if len(data) == 0:
        return data  # Ritorna lista vuota se non ci sono dati
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
    if len(temperature_data) < 2:
        return 0  # Ritorna 0 se non ci sono abbastanza dati per calcolare il trend
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
