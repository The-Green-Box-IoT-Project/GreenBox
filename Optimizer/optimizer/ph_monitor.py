# ph_monitor.py
from __future__ import annotations
from pathlib import Path
import csv
from dataclasses import dataclass
from typing import Optional

P = Path(__file__).parent
THRESHOLDS = P / "thresholds.csv"


@dataclass(frozen=True)
class Limits:
    lower: float
    upper: float


class PhMonitor:
    """
    Minimal event-driven pH monitor.
    - Reads pH limits from thresholds.csv.
    - On each new pH median:
        too low  -> notify "pH below range"
        too high -> notify "pH above range"
        in band  -> no action.
    - Returns a dict only if a new alert should be sent.
    """

    def __init__(self) -> None:
        self.limits = self._load_ph_limits(THRESHOLDS)
        self.last_state: Optional[str] = None  # "low", "high", or "ok"

    def decide(self, median_ph: float) -> Optional[dict]:
        lo, hi = self.limits.lower, self.limits.upper

        if median_ph < lo:
            state = "low"
            msg = f"pH too low ({median_ph:.2f} < {lo})"
        elif median_ph > hi:
            state = "high"
            msg = f"pH too high ({median_ph:.2f} > {hi})"
        else:
            state = "ok"
            msg = None

        # publish only on change (avoid duplicate alerts)
        if state != self.last_state:
            self.last_state = state
            if msg:
                return {"topic": "alerts/ph", "message": msg}
        return None

    @staticmethod
    def _load_ph_limits(path: Path) -> Limits:
        with path.open(newline="", encoding="utf-8") as f:
            for r in csv.DictReader(f):
                if r.get("metric", "").strip().lower() == "ph":
                    lower = float(r.get(" min", r.get("lower")))
                    upper = float(r.get(" max", r.get("upper")))
                    return Limits(lower=lower, upper=upper)
