from dataclasses import dataclass
from pathlib import Path
import csv
from typing import Dict, Tuple

P = Path(__file__).parent.absolute()
THRESHOLDS = P / "thresholds.csv"


@dataclass(frozen=True)
class Threshold:
    lower: float
    upper: float
    deadband: float

    @property
    def center(self) -> float:
        return 0.5 * (self.lower + self.upper)

    def band(self) -> Tuple[float, float]:
        lo = self.lower + self.deadband
        hi = self.upper - self.deadband
        return (lo, hi) if lo <= hi else (self.lower, self.upper)

    def in_band(self, x: float) -> bool:
        lo, hi = self.band()
        return lo <= x <= hi

    @classmethod
    def read_csv(cls) -> Dict[str, "Threshold"]:
        out: Dict[str, Threshold] = {}
        with THRESHOLDS.open(newline="", encoding="utf-8") as f:
            for r in csv.DictReader(f):
                rec = {k.strip().lower(): (v if v != "" else None) for k, v in r.items()}
                name_raw = (rec.get("metric") or "").strip()
                name = "pH" if name_raw.lower().replace("-", "").replace("_", "") == "ph" else name_raw
                lo = rec.get("lower", rec.get("min"))
                hi = rec.get("upper", rec.get("max"))
                db = rec.get("deadband", rec.get("dead_band", rec.get("tolerance", 0.0)))
                if lo is None or hi is None:
                    raise ValueError(f"Threshold missing bounds for metric '{name}'")
                out[name] = cls(float(lo), float(hi), float(db or 0.0))
        return out
