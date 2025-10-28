from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
import csv
from typing import Dict, Optional
from Actuators.actuator.actuator import Actuator

P = Path(__file__).parent
THRESHOLDS = P / "thresholds.csv"
LIGHT_SYSTEM = "illumination_system"


@dataclass(frozen=True)
class Band:
    lo: float
    hi: float


class LightOptimizer:
    """
    Event-driven, standalone light optimizer.
    - Reads 'light_natural' statistics (natural light only).
    - Uses Actuator(LIGHT_SYSTEM) to get levels and light effects.
    - Decision logic:
        ambient ≈ median_natural - effect[current_level]
        OFF if ambient >= lo
        otherwise ON at minimal level such that ambient + effect[level] >= lo
    - Publishes only on decision change (returns None otherwise).
    """

    def __init__(self) -> None:
        self.band = self._load_light_band(THRESHOLDS)

        act = Actuator(LIGHT_SYSTEM)
        self.levels = sorted(int(s.rstrip("%")) for s in act.levels)
        self.effect: Dict[int, float] = {
            int(str(k).rstrip("%")): float(v.get("light", 0.0))
            for k, v in act._by_level.items()
        }

        self.last_cmd: Optional[str] = None
        self.last_level: Optional[int] = None  # stores the last commanded level (0..100)

    def decide(self, median_lux: float) -> Optional[Dict[str, object]]:
        lo = self.band.lo
        curr_level = 0 if self.last_level is None else int(self.last_level)
        ambient = float(median_lux) - float(self.effect.get(curr_level, 0.0))

        if ambient >= lo:
            cmd = {"cmd": "OFF", "level": 0}
        else:
            target = next(
                (lvl for lvl in self.levels if lvl and ambient + self.effect.get(lvl, 0.0) >= lo),
                self.levels[-1],
            )
            cmd = {"cmd": "ON", "level": int(target)}

        if cmd["cmd"] != self.last_cmd or cmd["level"] != self.last_level:
            self.last_cmd, self.last_level = cmd["cmd"], cmd["level"]
            return cmd
        return None

    @staticmethod
    def _load_light_band(path: Path) -> Band:
        with path.open(newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for r in reader:
                if r.get("metric", "").strip().lower() == "light":
                    lower = float(r.get(" min", r.get("lower")))
                    upper = float(r.get(" max", r.get("upper")))
                    db = float(r.get(" deadband", r.get("deadband", 0.0)))
                    lo = lower + db
                    hi = upper - db
                    return Band(lo=lo, hi=(hi if hi >= lo else upper))
