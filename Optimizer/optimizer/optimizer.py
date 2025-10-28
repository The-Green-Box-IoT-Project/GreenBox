from dataclasses import dataclass
from itertools import product
from typing import Dict, List, Tuple, Any, Optional
from pathlib import Path
import csv
import math

from Actuators.actuator.actuator import Actuators, Actuator

P = Path(__file__).parent.absolute()


@dataclass(frozen=True)
class Threshold:
    lower: float
    upper: float
    deadband: float

    @property
    def center(self) -> float:
        return 0.5 * (self.lower + self.upper)


class Optimizer:
    """
    Multi-objective optimizer (excludes pH and Light):
      - Derives per-metric net derivatives from actuator effects.
      - Finds minimal time T to re-enter band for all out-of-band metrics.
      - Among feasible combos, minimizes weighted energy/water over T.
    """
    THRESHOLDS = P / "thresholds.csv"

    def __init__(self, *, weights: Dict[str, float] | None = None) -> None:
        self.thresholds = self._read_thresholds(self.THRESHOLDS)
        self.metrics: List[str] = [m for m in self.thresholds if m.lower() not in ("ph", "light")]

        systems = Actuators().systems
        self.actuators: Dict[str, Actuator] = {
            s: Actuator(s) for s in systems if not s.lower().startswith("light")
        }
        self.levels_by_actuator: Dict[str, List[int]] = {
            s: sorted(int(str(x).rstrip("%")) for x in a.levels) for s, a in self.actuators.items()
        }

        w = weights or {}
        self.w_energy = float(w.get("energy", 1.0))
        self.w_water = float(w.get("water", 1.0))

    def decide(
        self,
        per_metric_payloads: Dict[str, Dict[str, Any]],
        *,
        horizon_cap_s: Optional[float] = None,
    ) -> Dict[str, Any]:
        """
        Returns: {"mode","actions","duration_s","post_metrics","violation"}.
        """
        cur = self._current_from_payloads(per_metric_payloads)

        # HOLD if everything is already within band
        if all(self._in_band(cur.get(m, self.thresholds[m].center), self.thresholds[m]) for m in self.metrics):
            return {
                "mode": "hold",
                "actions": {a: self.actuators[a].level for a in self.actuators},
                "duration_s": 0.0,
                "post_metrics": dict(cur),
                "violation": self._violation_sum(cur),
            }

        # Search best combination
        acts = list(self.actuators)
        levels = [self.levels_by_actuator[a] for a in acts]

        best = {
            "key": (1, float("inf"), float("inf"), float("inf")),
            "actions": {a: self.actuators[a].level for a in acts},
            "T": 0.0,
            "post": dict(cur),
        }

        for combo in product(*levels):
            actions = {a: lvl for a, lvl in zip(acts, combo)}
            feasible, T, post, resid, e_rate, w_rate = self._time_to_band(cur, actions)
            if feasible and horizon_cap_s is not None and T > horizon_cap_s:
                continue
            key = self._score(feasible, T, resid, e_rate, w_rate)
            if key < best["key"]:
                best = {"key": key, "actions": actions, "T": T, "post": post}

        return {
            "mode": "optimized",
            "actions": best["actions"],
            "duration_s": float(best["T"]),
            "post_metrics": best["post"],
            "violation": self._violation_sum(best["post"]),
        }

    def _time_to_band(
        self,
        cur: Dict[str, float],
        actions: Dict[str, int],
    ) -> Tuple[bool, float, Dict[str, float], float, float, float]:
        # net derivative for each metric; consumption rates
        net = {m: 0.0 for m in self.metrics}
        e_rate = 0.0
        w_rate = 0.0

        for a, lvl in actions.items():
            row = self._effects_for(a, lvl)
            for col, val in row.items():
                if not self._finite(val):
                    continue
                cl = str(col).lower()
                if cl.startswith("energy_consumption"):
                    e_rate += float(val)
                elif cl.startswith("water_consumption"):
                    w_rate += float(val)
                elif col in net:
                    net[col] += float(val)

        T_req = 0.0         # min time to enter band for all violated metrics
        T_max = float("inf")  # max time before leaving band for already-in-band metrics

        for m in self.metrics:
            th = self.thresholds[m]
            x = float(cur.get(m, th.center))
            lo, hi = self._band(th)
            dx = net.get(m, 0.0)

            if x < lo:
                if dx <= 0:
                    return False, 0.0, dict(cur), self._violation_sum(cur), e_rate, w_rate
                T_req = max(T_req, (lo - x) / dx)
            elif x > hi:
                if dx >= 0:
                    return False, 0.0, dict(cur), self._violation_sum(cur), e_rate, w_rate
                T_req = max(T_req, (x - hi) / (-dx))
            else:
                if dx > 0:
                    T_max = min(T_max, (hi - x) / dx)
                elif dx < 0:
                    T_max = min(T_max, (x - lo) / (-dx))

        if T_req > T_max:
            return False, 0.0, dict(cur), self._violation_sum(cur), e_rate, w_rate

        T = max(0.0, T_req)
        post = {m: float(cur.get(m, self.thresholds[m].center)) + net.get(m, 0.0) * T for m in self.metrics}
        resid = self._violation_sum(post)
        return True, float(T), post, resid, e_rate, w_rate

    def _score(self, feasible: bool, T: float, resid: float, e_rate: float, w_rate: float) -> Tuple:
        if feasible:
            # Primary: minimal T; Secondary: weighted resource use over horizon
            return 0, float(T), self.w_energy * e_rate * float(T), self.w_water * w_rate * float(T)
        # Infeasible combos sort after all feasible ones; smaller residual is better
        return 1, float("inf"), float(resid), 0.0

    def _current_from_payloads(self, payloads: Dict[str, Dict[str, Any]]) -> Dict[str, float]:
        """Pick 'median' for each metric; fallback to threshold center if missing."""
        out: Dict[str, float] = {}
        for m, p in (payloads or {}).items():
            v = p.get("median", None)
            if self._finite(v):
                out[m] = float(v)
        for m, th in self.thresholds.items():
            if m not in out and m.lower() not in ("ph", "light"):
                out[m] = th.center
        return out

    def _read_thresholds(self, path: Path) -> Dict[str, Threshold]:
        out: Dict[str, Threshold] = {}
        with path.open(newline="", encoding="utf-8") as f:
            for r in csv.DictReader(f):
                rec = {k.strip().lower(): (v if v != "" else None) for k, v in r.items()}
                name_raw = (rec.get("metric") or "").strip()
                name = "pH" if name_raw.lower().replace("-", "").replace("_", "") == "ph" else name_raw
                lo = rec.get("lower", rec.get("min"))
                hi = rec.get("upper", rec.get("max"))
                db = rec.get("deadband", rec.get("dead_band", rec.get("tolerance", 0.0)))
                if lo is None or hi is None:
                    raise ValueError(f"Threshold missing bounds for metric '{name}'")
                out[name] = Threshold(float(lo), float(hi), float(db or 0.0))
        return out

    @staticmethod
    def _finite(x: Any) -> bool:
        try:
            return x is not None and math.isfinite(float(x))
        except Exception:
            return False

    @staticmethod
    def _band(th: Threshold) -> Tuple[float, float]:
        lo = th.lower + th.deadband
        hi = th.upper - th.deadband
        return (lo, hi) if lo <= hi else (th.lower, th.upper)

    def _in_band(self, x: float, th: Threshold) -> bool:
        lo, hi = self._band(th)
        return lo <= x <= hi

    def _violation_sum(self, metrics: Dict[str, float]) -> float:
        s = 0.0
        for m, th in self.thresholds.items():
            if m.lower() in ("ph", "light"):
                continue
            x = metrics.get(m, th.center)
            lo, hi = self._band(th)
            if not self._finite(x):
                s += abs(0.5 * (lo + hi))
            else:
                xv = float(x)
                if xv < lo:
                    s += lo - xv
                elif xv > hi:
                    s += xv - hi
        return s

    def _effects_for(self, system: str, level: int) -> Dict[str, float]:
        """Row of effects.csv for (system, level)."""
        act = self.actuators[system]
        try:
            row = act._by_level(level)  # if implemented as a method
        except TypeError:
            row = act._by_level.get(f"{int(level)}%", {})
        return {k: float(v) for k, v in (row or {}).items() if self._finite(v)}
