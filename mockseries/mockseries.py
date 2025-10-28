import json
from datetime import timedelta
from typing import Dict
import numpy as np
import pandas as pd
from pathlib import Path
import os
from dotenv import load_dotenv
from utils.tools import Today, get_latest_entry_before_now

load_dotenv()

P = Path(__file__).resolve().parent  # cartella del modulo


def datetime_range(granularity: timedelta, start_time, end_time) -> pd.DatetimeIndex:
    """Return a left-inclusive, right-exclusive DatetimeIndex with lowercase freq."""
    if start_time is None or end_time is None:
        raise ValueError("start_time and end_time are required.")
    step = int(granularity.total_seconds())
    if step % 3600 == 0:
        freq = f"{step // 3600}h"
    elif step % 60 == 0:
        freq = f"{step // 60}min"
    else:
        freq = f"{step}s"
    return pd.date_range(start=start_time, end=end_time, freq=freq, inclusive="left")


class LinearTrend:
    """Linear baseline: flat_base + coefficient * (elapsed / time_unit)."""
    def __init__(self, coefficient: float, time_unit: timedelta, flat_base: float = 0.0):
        self.coefficient = float(coefficient)
        self.time_unit = time_unit
        self.flat_base = float(flat_base)

    def evaluate(self, index: pd.DatetimeIndex) -> pd.Series:
        t0 = index[0]
        units = (index - t0) / self.time_unit
        values = self.flat_base + self.coefficient * units.values.astype(float)
        return pd.Series(values, index=index)


class _PeriodicSeasonality:
    """Cyclic, piecewise-linear interpolation over a fixed period (seconds)."""
    def __init__(self, knots: Dict[timedelta, float], seconds_period: int):
        if not knots:
            self.knots_s = np.array([0.0], dtype=float)
            self.knots_v = np.array([0.0], dtype=float)
        else:
            items = sorted(((td.total_seconds(), float(val)) for td, val in knots.items()), key=lambda p: p[0])
            self.knots_s = np.array([a for a, _ in items], dtype=float)
            self.knots_v = np.array([b for _, b in items], dtype=float)
        self.period = float(seconds_period)

    def _interp(self, seconds_in_period: np.ndarray) -> np.ndarray:
        x = np.mod(seconds_in_period, self.period)
        if self.knots_s.size == 1:
            return np.full_like(x, self.knots_v[0], dtype=float)
        idx = np.searchsorted(self.knots_s, x, side="right") - 1
        idx = np.clip(idx, 0, self.knots_s.size - 2)
        x0, x1 = self.knots_s[idx], self.knots_s[idx + 1]
        y0, y1 = self.knots_v[idx], self.knots_v[idx + 1]
        w = (x - x0) / np.where((x1 - x0) == 0.0, 1.0, (x1 - x0))
        return y0 + w * (y1 - y0)


class DailySeasonality(_PeriodicSeasonality):
    """Daily cycle from hour-offset knots within 24h."""
    def __init__(self, knots: Dict[timedelta, float]):
        super().__init__(knots, 24 * 3600)

    def evaluate(self, index: pd.DatetimeIndex) -> pd.Series:
        seconds = (index - index.normalize()).total_seconds()
        return pd.Series(self._interp(seconds), index=index)


class YearlySeasonality(_PeriodicSeasonality):
    """Yearly cycle from day-offset knots within a 365-day year (approx)."""
    def __init__(self, knots: Dict[timedelta, float]):
        super().__init__(knots, 365 * 24 * 3600)

    def evaluate(self, index: pd.DatetimeIndex) -> pd.Series:
        year_start = pd.to_datetime([
            pd.Timestamp(ts).replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
            for ts in index
        ])
        seconds = (index - year_start).total_seconds()
        return pd.Series(self._interp(seconds), index=index)


class RedNoise:
    """AR(1) noise with marginal std≈std and lag-1 corr≈rho."""
    def __init__(self, mean: float = 0.0, std: float = 1.0, correlation: float = 0.0, seed: int | None = None):
        self.mean = float(mean)
        self.std = float(std)
        self.rho = float(correlation)
        self.rng = np.random.default_rng(seed)

    def evaluate(self, index: pd.DatetimeIndex) -> pd.Series:
        n = len(index)
        if n == 0:
            return pd.Series(dtype=float, index=index)
        eps_std = self.std * np.sqrt(max(1e-12, 1.0 - self.rho ** 2))
        x = np.empty(n, dtype=float)
        x[0] = self.rng.normal(self.mean, self.std)
        for t in range(1, n):
            x[t] = self.mean + self.rho * (x[t - 1] - self.mean) + self.rng.normal(0.0, eps_std)
        return pd.Series(x, index=index)


class Measure:
    """Measurement configuration and generator from JSON."""
    SIMULATE = os.environ.get("SIMULATE", "real")

    def __init__(self, base: float, daily: Dict[timedelta, float], yearly: Dict[timedelta, float], noise: dict):
        self.base = float(base)
        self.daily_knots = daily
        self.yearly_knots = yearly
        self.noise = {
            "mean": float(noise.get("mean", 0.0)),
            "std": float(noise.get("std", 1.0)),
            "correlation": float(noise.get("correlation", 0.0)),
        }

    @classmethod
    def from_json(cls, name: str) -> "Measure":
        path = cls._get_data_file_path()
        with open(path, "r", encoding="utf-8") as f:
            all_data = json.load(f)
        if name not in all_data:
            raise ValueError(
                f"Measurement '{name}' not found in {path.name}. "
                f"Available: {', '.join(sorted(all_data.keys()))}"
            )
        data = all_data[name]
        daily = {} if not data.get("daily_seasonality") else {
            timedelta(hours=h): v
            for h, v in zip(data["daily_seasonality"]["times"], data["daily_seasonality"]["values"])
        }
        yearly = {} if not data.get("yearly_seasonality") else {
            timedelta(days=d): v
            for d, v in zip(data["yearly_seasonality"]["times"], data["yearly_seasonality"]["values"])
        }
        return cls(
            base=data["base_value"],
            daily=daily,
            yearly=yearly,
            noise=data.get("noise", {"mean": 0.0, "std": 0.5, "correlation": 0.5}),
        )

    @classmethod
    def _get_data_file_path(cls) -> Path:
        """
        Returns the path to '<simulate>.json' in the same folder as the module.
        Example: simulate='real' -> '<here>/real.json'.
        """
        path = P / f"{cls.SIMULATE}.json"
        if path.is_file():
            return path
        available = sorted(p.stem for p in P.glob("*.json"))
        raise FileNotFoundError(
            f"Simulate must be one of {available} (missing file: {path.name})"
        )

    def generate(self, name: str, index: pd.DatetimeIndex) -> pd.Series:
        """Compose base + seasonality (+ noise); for 'light' use daily*yearly."""
        base = pd.Series(self.base, index=index, dtype=float)
        d = DailySeasonality(self.daily_knots).evaluate(index)
        y = YearlySeasonality(self.yearly_knots).evaluate(index)
        n = RedNoise(**self.noise).evaluate(index)
        s = base + (d * y if name == "light" else d + y) + n
        return s.clip(lower=0) if name == "light" else s


class SimulateRealTimeReading:
    """Generate today's series and sample a 1s-resolution value up to now."""
    def __init__(self, measurement_name: str):
        self.name = measurement_name
        self.measure = Measure.from_json(measurement_name)
        today = Today()
        self.index = datetime_range(timedelta(hours=1), today.start_day, today.end_day)

    def read(self) -> float:
        s = self.measure.generate(self.name, self.index)
        t0 = get_latest_entry_before_now(s) or self.index[0]  # fallback alle 00:00
        window = s.loc[t0: t0 + timedelta(hours=1)].astype(float)
        resampled = window.resample("1s").interpolate("linear").round(2)
        ts = get_latest_entry_before_now(resampled) or resampled.index[0]
        return float(resampled.loc[ts])
