from itertools import product
from typing import Dict, List, Tuple, Any, Optional
import math
import pandas as pd

from greenbox.sim.thresholds.thresholds import Threshold


class Optimizer:
    """
    Multi-objective optimizer (excludes pH and Light):
      - Derives per-metric net derivatives from actuator effects.
      - Finds minimal time T to re-enter band for all out-of-band metrics.
      - Among feasible combos, minimizes weighted energy/water over T.
    """

    def __init__(
        self,
        thresholds_config: Dict[str, Threshold],
        effects_config_df: pd.DataFrame,
        *,
        weights: Dict[str, float] | None = None,
    ) -> None:

        self.thresholds = thresholds_config
        self.metrics: List[str] = [
            m for m in self.thresholds if m.lower() not in ("ph", "light")
        ]

        # Process effects_config_df to build internal actuator models
        self.actuators: Dict[str, Dict[str, Dict[str, float]]] = {}
        self.levels_by_actuator: Dict[str, List[int]] = {}

        all_systems = sorted(effects_config_df["system"].dropna().unique().tolist())
        systems = [s for s in all_systems if not s.lower().startswith("light")]

        for s in systems:
            sys_df = effects_config_df[effects_config_df["system"] == s]
            self.levels_by_actuator[s] = sorted(
                int(str(x).rstrip("%")) for x in sys_df["level"].unique()
            )

            levels_data = {}
            for _, r in sys_df.iterrows():
                level_key = str(r["level"])
                effects_data = r.drop(labels=["system", "level"]).dropna().to_dict()
                levels_data[level_key] = {k: float(v) for k, v in effects_data.items()}
            self.actuators[s] = levels_data

        w = weights or {}
        self.w_energy = float(w.get("energy", 1.0))
        self.w_water = float(w.get("water", 1.0))

    def decide(
        self,
        per_metric_payloads: Dict[str, Dict[str, Any]],
        *,
        horizon_cap_s: Optional[float] = None,
        current_actuator_state: Dict[str, Any] # Aggiunto current_actuator_state
    ) -> Dict[str, Any]:
        """
        Returns: {"mode","actions","duration_s","post_metrics","violation"}.
        """
        cur = self._current_from_payloads(per_metric_payloads)

        # HOLD if everything is already within band
        if all(
            self.thresholds[m].in_band(cur.get(m, self.thresholds[m].center))
            for m in self.metrics
        ):
            return {
                "mode": "hold",
                "actions": current_actuator_state, # In modalità hold, mantiene lo stato attuale
                "post_metrics": dict(cur),
                "violation": self._violation_sum(cur),
            }

        # Search best combination
        acts = list(self.actuators)
        levels = [self.levels_by_actuator[a] for a in acts]

        best = {
            "key": (1, float("inf"), float("inf"), float("inf")),
            "actions": {a: 0 for a in acts},  # Default to off
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
            # "duration_s": float(best["T"]), # Rimosso duration_s
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
            level_key = f"{int(lvl)}%"
            # Find the row of effects for the given actuator and level
            row = self.actuators.get(a, {}).get(
                level_key, self.actuators.get(a, {}).get(str(int(lvl)))
            )
            if not row:
                continue

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

        T_req = 0.0  # min time to enter band for all violated metrics
        T_max = float("inf")  # max time before leaving band for already-in-band metrics

        for m in self.metrics:
            th = self.thresholds[m]
            x = float(cur.get(m, th.center))
            lo, hi = th.band()
            dx = net.get(m, 0.0)

            if x < lo:
                if dx <= 0:
                    return (
                        False,
                        0.0,
                        dict(cur),
                        self._violation_sum(cur),
                        e_rate,
                        w_rate,
                    )
                T_req = max(T_req, (lo - x) / dx)
            elif x > hi:
                if dx >= 0:
                    return (
                        False,
                        0.0,
                        dict(cur),
                        self._violation_sum(cur),
                        e_rate,
                        w_rate,
                    )
                T_req = max(T_req, (x - hi) / (-dx))
            else:
                if dx > 0:
                    T_max = min(T_max, (hi - x) / dx)
                elif dx < 0:
                    T_max = min(T_max, (x - lo) / (-dx))

        if T_req > T_max:
            return False, 0.0, dict(cur), self._violation_sum(cur), e_rate, w_rate

        T = max(0.0, T_req)
        post = {
            m: float(cur.get(m, self.thresholds[m].center)) + net.get(m, 0.0) * T
            for m in self.metrics
        }
        resid = self._violation_sum(post)
        return True, float(T), post, resid, e_rate, w_rate

    def _score(
        self, feasible: bool, T: float, resid: float, e_rate: float, w_rate: float
    ) -> Tuple:
        if feasible:
            # Primary: minimal T; Secondary: weighted resource use over horizon
            return (
                0,
                float(T),
                self.w_energy * e_rate * float(T),
                self.w_water * w_rate * float(T),
            )
        # Infeasible combos sort after all feasible ones; smaller residual is better
        return 1, float("inf"), float(resid), 0.0

    def _current_from_payloads(
        self, payloads: Dict[str, Dict[str, Any]]
    ) -> Dict[str, float]:
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

    @staticmethod
    def _finite(x: Any) -> bool:
        try:
            return x is not None and math.isfinite(float(x))
        except Exception:
            return False

    def _violation_sum(self, metrics: Dict[str, float]) -> float:
        s = 0.0
        for m, th in self.thresholds.items():
            if m.lower() in ("ph", "light"):
                continue
            x = metrics.get(m, th.center)
            lo, hi = th.band()
            if not self._finite(x):
                s += abs(0.5 * (lo + hi))
            else:
                xv = float(x)
                if xv < lo:
                    s += lo - xv
                elif xv > hi:
                    s += xv - hi
        return s


class LightOptimizer:
    """
    Event-driven, standalone light optimizer.
    - Reads 'light' band from Threshold.
    - Uses Effects("illumination_system") to get levels and light effects.
    - Decision logic:
        ambient ≈ median_natural - effect[current_level]
        OFF if ambient >= lo
        otherwise ON at minimal level such that ambient + effect[level] >= lo
    - Publishes only on decision change (returns None otherwise).
    """

    def __init__(
        self, thresholds_config: Dict[str, Threshold], effects_config_df: pd.DataFrame
    ) -> None:
        light_threshold = None
        for key, value in thresholds_config.items():
            if key.lower() == "light":
                light_threshold = value
                break
        if light_threshold is None:
            raise ValueError("Fatal: 'light' threshold configuration not found.")

        self.lo, self.hi = light_threshold.band()

        # Filter effects for illumination_system
        sys_df = effects_config_df[effects_config_df["system"] == "illumination_system"]
        self.levels = sorted(int(s.rstrip("%")) for s in sys_df["level"].unique())

        self.effect: Dict[int, float] = {}
        for _, r in sys_df.iterrows():
            level_key = int(r["level"].rstrip("%"))
            self.effect[level_key] = float(r.get("light", 0.0))

        self.last_cmd: Optional[str] = None
        self.last_level: Optional[int] = (
            None  # stores the last commanded level (0..100)
        )

    def decide(self, median_lux: float) -> Optional[Dict[str, object]]:
        lo = self.lo
        curr_level = 0 if self.last_level is None else int(self.last_level)
        ambient = float(median_lux) - float(self.effect.get(curr_level, 0.0))

        if ambient >= lo:
            cmd = {"cmd": "OFF", "level": 0}
        else:
            target = next(
                (
                    lvl
                    for lvl in self.levels
                    if lvl and ambient + self.effect.get(lvl, 0.0) >= lo
                ),
                self.levels[-1] if self.levels else 0,  # Handle case with no levels
            )
            cmd = {"cmd": "ON", "level": int(target)}

        if cmd["cmd"] != self.last_cmd or cmd["level"] != self.last_level:
            self.last_cmd, self.last_level = cmd["cmd"], cmd["level"]
            return cmd
        return None


class PhMonitor:
    """Emit an alert when pH goes out of limits; publish only on state change."""

    def __init__(self, thresholds_config: Dict[str, Threshold]) -> None:
        ph_threshold = None
        for key, value in thresholds_config.items():
            if key.lower() == "ph":
                ph_threshold = value
                break
        if ph_threshold is None:
            raise ValueError("Fatal: 'pH' threshold configuration not found.")

        self.lo, self.hi = ph_threshold.lower, ph_threshold.upper
        self.last_state: Optional[str] = None

    def decide(self, median_ph: float) -> Optional[dict]:
        lo, hi = self.lo, self.hi

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
