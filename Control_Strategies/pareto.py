from dataclasses import dataclass
from itertools import product
from typing import Dict, List, Tuple
import numpy as np
import pandas as pd
import re
from pprint import pprint

from utils.tools import read_env, select_last_measurements

METRICS = ["temperature", "humidity", "pH", "soil_humidity", "light"]

@dataclass(frozen=True)
class Threshold:
    lower: float
    upper: float
    deadband: float

    @property
    def center(self) -> float:
        return (self.lower + self.upper) / 2.0


@dataclass(frozen=True)
class ActuatorOption:
    actuator: str
    level: int
    deltas: Dict[str, float]    # delta per secondo per metrica
    energy: float               # consumo "rate" per secondo (se fosse per ora: dividere /3600 a load)
    water: float                # consumo "rate" per secondo


# -----------------------
# Ottimizzatore
# -----------------------
class GreenhouseOptimizer:
    """
    Politica:
      - HOLD se tutte le metriche sono dentro la banda accettabile (deadband).
      - Altrimenti, tra tutte le combinazioni di livelli:
           1) scegli solo le FATTIBILI: esiste una durata T che porta tutte le metriche fuori soglia
              dentro la banda accettabile SENZA far uscire quelle già buone;
           2) minimizza T;
           3) a parità di T, minimizza energia*T, acqua*T e (opz.) switch.

    CSV attesi:
      thresholds.csv: metric, min, max, deadband  (spazi nelle intestazioni ok)
      actuators_effect.csv: system, level, energy_consumption..., water_consumption...
                            temperature [K/s], humidity [%/s], light [.../s],
                            soil_humidity [/s], pH [pH/s]
    """

    def __init__(
        self,
        df_last_24h: pd.DataFrame,
        thresholds_csv: str,
        effects_csv: str,
        *,
        weights: Dict[str, float] | None = None,    # pesi per costi (energia, acqua, switch)
        previous_levels: Dict[str, int] | None = None,
        use_switching_cost: bool = False,
    ) -> None:
        self.df = df_last_24h.copy()
        self.df.index = pd.to_datetime(self.df.index)
        self.df = self.df.sort_index()

        self.thresholds = self._load_thresholds(thresholds_csv)
        self.options_by_actuator = self._load_effects(effects_csv)

        # elenco canonico attuatori come da CSV (serve a _canon)
        self.actuators = list(self.options_by_actuator.keys())

        # pesi per i costi (usati solo nel tie-break a parità di T)
        self.w = {"energy": 1.0, "water": 1.0, "switch": 0.0}
        if weights:
            self.w.update({k: float(v) for k, v in weights.items()})
        self.w["switch"] = self.w["switch"] if use_switching_cost else 0.0

        # livelli disponibili per attuatore (ordinati)
        self._levels_by_actuator = {
            a: sorted(o.level for o in opts) for a, opts in self.options_by_actuator.items()
        }

        # default "corrente": 0 se presente, altrimenti minimo disponibile
        self.previous_levels = {
            a: (0 if 0 in self._levels_by_actuator[a] else self._levels_by_actuator[a][0])
            for a in self.options_by_actuator
        }
        # applica eventuali livelli passati
        if previous_levels:
            for k, v in previous_levels.items():
                if k is not None:
                    avail = self._levels_by_actuator[k]
                    lvl = int(v)
                    self.previous_levels[k] = min(avail, key=lambda x: abs(x - lvl))

    # -----------------------
    # API
    # -----------------------
    def decide(self, *, horizon_cap_s: float | None = None) -> Dict:
        """
        horizon_cap_s: opzionale, scarta piani che richiedono più tempo (es. 1800 per max 30 min).
        """
        current = self._latest_metrics()

        # se tutte dentro la banda accettabile -> HOLD
        if all(self._in_band(current.get(m, th.center), th) for m, th in self.thresholds.items()):
            return {
                "mode": "hold",
                "actions": {a: self.previous_levels[a] for a in self.actuators},
                "post_metrics": current,
                "reason": "Tutte le metriche sono dentro la banda accettabile (deadband).",
                "duration_s": 0.0,
            }

        actions, T, post = self._search_best_actions(current, horizon_cap_s=horizon_cap_s)
        # se non abbiamo trovato piani fattibili (es. nessun attuatore muove nella direzione utile)
        if T == 0.0 and actions == {a: self.previous_levels[a] for a in self.actuators}:
            return {
                "mode": "optimized",
                "actions": actions,
                "duration_s": 0.0,
                "post_metrics": post,
                "violation": self._violation_sum_band(post),
                "note": "Nessuna combinazione fattibile per rientrare entro la deadband; mantenuto HOLD.",
            }

        return {
            "mode": "optimized",
            "actions": actions,
            "duration_s": T,
            "post_metrics": post,
            "violation": self._violation_sum_band(post),
        }

    # -----------------------
    # Loader CSV
    # -----------------------
    def _load_thresholds(self, path: str) -> Dict[str, Threshold]:
        tdf = pd.read_csv(path)
        tdf.columns = [c.strip() for c in tdf.columns]
        cols = {c.lower(): c for c in tdf.columns}

        metric_col = cols.get("metric")
        lower_col = cols.get("lower") or cols.get("min")
        upper_col = cols.get("upper") or cols.get("max")
        dead_col = cols.get("deadband") or cols.get("dead_band") or cols.get("tolerance")

        missing = [n for n, c in {
            "metric": metric_col, "lower/min": lower_col, "upper/max": upper_col, "deadband": dead_col
        }.items() if c is None]
        if missing:
            raise ValueError(f"thresholds.csv: colonne mancanti {missing}")

        out: Dict[str, Threshold] = {}
        for _, r in tdf.iterrows():
            m_raw = str(r[metric_col]).strip()
            # Se è una variante di pH, normalizza alla CHIAVE "pH" (niente 'ph' minuscolo)
            m = "pH" if m_raw.lower().replace("-", "").replace("_", "") == "ph" else m_raw
            out[m] = Threshold(
                lower=float(r[lower_col]),
                upper=float(r[upper_col]),
                deadband=float(r[dead_col]),
            )
        unknown = set(out) - set(METRICS)
        if unknown:
            raise ValueError(f"thresholds.csv: metriche sconosciute: {sorted(unknown)} (attese: {METRICS})")
        return out

    def _load_effects(self, path: str) -> Dict[str, List[ActuatorOption]]:
        edf = pd.read_csv(path)
        edf.columns = [c.strip() for c in edf.columns]

        actuator_col = "system" if "system" in edf.columns else "actuator"
        level_col = "level"
        energy_col = next((c for c in edf.columns if c.lower().startswith("energy_consumption")), None)
        water_col = next((c for c in edf.columns if c.lower().startswith("water_consumption")), None)

        # trova colonne delta con unità reali
        delta_cols: Dict[str, str] = {}
        for c in edf.columns:
            cl = c.lower()
            if "temperature" in cl and "consumption" not in cl:
                delta_cols["temperature"] = c
            elif cl.startswith("humidity") and "consumption" not in cl:
                delta_cols["humidity"] = c
            elif "soil_humidity" in cl:
                delta_cols["soil_humidity"] = c
            elif cl.startswith("light"):
                delta_cols["light"] = c
            elif "ph" in cl and "consumption" not in cl:
                # accetta "pH", "ph", "p_h", "p-h", ecc. — la CHIAVE resta "pH"
                delta_cols["pH"] = c

        groups: Dict[str, List[ActuatorOption]] = {}
        for _, r in edf.iterrows():
            a = str(r[actuator_col]).strip()
            lvl_raw = r[level_col]
            if isinstance(lvl_raw, str):
                m = re.search(r"\d+", lvl_raw)
                lvl = int(m.group(0)) if m else 0
            else:
                lvl = int(lvl_raw)

            deltas = {}
            for mtr, col in delta_cols.items():
                val = r.get(col, 0.0)
                deltas[mtr] = float(val) if pd.notna(val) else 0.0

            e_val = r.get(energy_col, 0.0) if energy_col else 0.0
            w_val = r.get(water_col, 0.0) if water_col else 0.0
            energy = float(e_val) if pd.notna(e_val) else 0.0
            water = float(w_val) if pd.notna(w_val) else 0.0

            # livello 0 neutro
            if lvl == 0:
                deltas = {m: 0.0 for m in METRICS}
                energy = 0.0
                water = 0.0

            groups.setdefault(a, []).append(ActuatorOption(a, lvl, deltas, energy=energy, water=water))

        for a in groups:
            groups[a].sort(key=lambda o: o.level)
        return groups

    # -----------------------
    # Ricerca piano + durata (obiettivo lessicografico)
    # -----------------------
    def _search_best_actions(self, current: Dict[str, float], *, horizon_cap_s: float | None = None
                             ) -> Tuple[Dict[str, int], float, Dict[str, float]]:
        acts = list(self.options_by_actuator)
        levels = [[o.level for o in self.options_by_actuator[a]] for a in acts]

        # baseline: HOLD (T=0)
        hold_actions = {a: self.previous_levels[a] for a in acts}
        feasible, T_hold, post_hold, resid_hold, en_rate_hold, wa_rate_hold, sw_hold = \
            self._time_to_target(current, hold_actions)
        # se HOLD non è fattibile, lo teniamo come fallback ma perderà contro qualunque piano fattibile
        best_key = self._score_key(feasible, T_hold, resid_hold, en_rate_hold, wa_rate_hold, sw_hold)
        best_actions, best_T, best_post = hold_actions, T_hold, post_hold

        for combo in product(*levels):
            actions = {a: lvl for a, lvl in zip(acts, combo)}
            feasible, T, post, residual, energy_rate, water_rate, switches = \
                self._time_to_target(current, actions)

            # scarta piani troppo lenti
            if feasible and horizon_cap_s is not None and T > horizon_cap_s:
                continue

            key = self._score_key(feasible, T, residual, energy_rate, water_rate, switches)
            if key < best_key:
                best_key, best_actions, best_T, best_post = key, actions, T, post

        return best_actions, float(best_T), best_post

    def _score_key(self, feasible: bool, T: float, residual: float,
                   energy_rate: float, water_rate: float, switches: int) -> Tuple:
        """
        Ordine lessicografico:
          (is_infeasible, T, energy_cost, water_cost, switch_cost)
        dove is_infeasible = 0 se fattibile, 1 altrimenti.
        NOTA: per i piani non fattibili usiamo T=fisso grande e residual come tie-break.
        """
        if feasible:
            return (0, float(T),
                    self.w["energy"] * energy_rate * T,
                    self.w["water"] * water_rate * T,
                    self.w["switch"] * switches)
        else:
            # residuo come 2° criterio; T fisso alto per tenerli dopo i fattibili
            BIG_T = 1e12
            return (1, BIG_T, residual, self.w["switch"] * switches, 0.0)

    # -----------------------
    # Dinamica “tempo per rientrare”
    # -----------------------
    def _band_bounds(self, th: Threshold) -> Tuple[float, float]:
        """Intervallo accettabile: entro deadband se possibile, altrimenti [lower, upper]."""
        lo = th.lower + th.deadband
        hi = th.upper - th.deadband
        if lo <= hi:
            return lo, hi
        return th.lower, th.upper

    def _in_band(self, val: float, th: Threshold) -> bool:
        lo, hi = self._band_bounds(th)
        return lo <= val <= hi

    def _time_to_target(self, current, actions):
        net = {m: 0.0 for m in METRICS}
        energy_rate = 0.0
        water_rate = 0.0
        switches = 0

        # luce additiva (ON/OFF)
        additive_light = 0.0
        for a, lvl in actions.items():
            opt = next(o for o in self.options_by_actuator[a] if o.level == lvl)
            energy_rate += float(opt.energy)
            water_rate += float(opt.water)
            switches += int(lvl != self.previous_levels.get(a, lvl))

            if a.lower().strip() == "illumination_system" and lvl > 0:
                # contributo additivo istantaneo
                additive_light += float(opt.deltas.get("light", 0.0))
            else:
                # rate/s per tutte le metriche (eccetto light per l'illumination_system)
                for m, dps in opt.deltas.items():
                    if not (m == "light" and a.lower().strip() == "illumination_system"):
                        if m in net:  # evita KeyError su metriche non attese
                            net[m] += float(dps)

        # calcolo T per metriche continue (NO light)
        T_req = 0.0
        T_max = float("inf")
        infeasible = False
        for m, th in self.thresholds.items():
            if m == "light":
                continue  # la luce è gestita come ON/OFF additivo

            val = float(current.get(m, th.center))
            lo, hi = self._band_bounds(th)
            d = net.get(m, 0.0)

            if val < lo:
                if d <= 0:
                    infeasible = True
                    break
                T_req = max(T_req, (lo - val) / d)
            elif val > hi:
                if d >= 0:
                    infeasible = True
                    break
                T_req = max(T_req, (val - hi) / (-d))

            if lo <= val <= hi:
                if d > 0:
                    T_max = min(T_max, (hi - val) / d)
                elif d < 0:
                    T_max = min(T_max, (val - lo) / (-d))

        # verifica fattibilità specifica della luce (istantanea)
        if not infeasible:
            th_l = self.thresholds["light"]
            lo_l, hi_l = self._band_bounds(th_l)
            v_light_post = float(current.get("light", th_l.center)) + additive_light
            if not (lo_l <= v_light_post <= hi_l):
                infeasible = True

        if infeasible or T_req > T_max:
            residual = self._violation_sum_band(current)
            return False, 0.0, dict(current), residual, energy_rate, water_rate, switches

        T = max(0.0, T_req)

        # stato post-attuazione (NO clamp)
        post = {}
        for m, th in self.thresholds.items():
            v0 = float(current.get(m, th.center))
            if m == "light":
                post[m] = v0 + additive_light  # additivo istantaneo
            else:
                post[m] = v0 + net.get(m, 0.0) * T

        residual = self._violation_sum_band(post)

        # durata: se la luce è ON, 3600s; altrimenti T continuo
        light_on = additive_light > 0.0
        T_out = 3600.0 if light_on else T

        return True, T_out, post, residual, energy_rate, water_rate, switches

    # -----------------------
    # Metriche, violazioni, utilità
    # -----------------------
    def _violation_sum_band(self, metrics: Dict[str, float]) -> float:
        """Somma violazioni rispetto alla banda accettabile (deadband)."""
        s = 0.0
        for m, th in self.thresholds.items():
            val = metrics.get(m)
            lo, hi = self._band_bounds(th)
            if val is None or not np.isfinite(val):
                s += abs((lo + hi) / 2.0)
                continue
            if val < lo:
                s += (lo - val)
            elif val > hi:
                s += (val - hi)
        return s

    def _latest_metrics(self) -> Dict[str, float]:
        if self.df.empty:
            raise ValueError("df_last_24h è vuoto.")
        row = self.df.iloc[-1]

        # helper per trovare la colonna giusta (rispetta 'pH' come chiave logica)
        def find_col(candidates):
            # match esatto (case-sensitive) prima
            for cand in candidates:
                if cand in row.index:
                    return cand
            # poi match case-insensitive
            low_map = {str(c).strip().lower(): c for c in row.index}
            for cand in candidates:
                key = cand.lower()
                if key in low_map:
                    return low_map[key]
            return None

        mapping = {
            "temperature": find_col(["temperature", "Temperature"]),
            "humidity": find_col(["humidity", "Humidity", "relative_humidity"]),
            "soil_humidity": find_col(
                ["soil_humidity", "Soil_humidity", "soil_moisture", "Soil_moisture", "soil moisture"]),
            "light": find_col(["light", "Light", "illuminance", "Illuminance"]),
            "pH": find_col(["pH", "PH", "Ph", "p_h", "p-h", "ph"]),  # -> chiave sempre "pH"
        }

        out = {}
        for m, col in mapping.items():
            if col is not None and pd.notna(row[col]):
                out[m] = float(row[col])
        return out


# -----------------------
# Esempio d'uso minimo
# -----------------------
if __name__ == "__main__":
    # Esempio stato corrente
    current = {
        "temperature": 20.0,
        "humidity": 75.0,
        "pH": 5.0,
        "soil_humidity": 80.0,
        "light": 500.0,
    }

    read_env()

    current = select_last_measurements()
    del current['timestamp']
    pprint(current)

    # Esempio ultimo stato attuatori
    previous = {"illumination_system": 0, "irrigation_system": 0, "ventilation_system": 0, "heating_system": 0, "humidification_system": 0}

    # Grado di importanza
    WEIGHTS = {"energy": 1.0, "water": 1.0, "switch": 0.2}

    df = pd.DataFrame([current], index=[pd.Timestamp.utcnow()])

    opt = GreenhouseOptimizer(
        df_last_24h=df,
        thresholds_csv="thresholds.csv",
        effects_csv="actuators_effect.csv",
        weights=WEIGHTS,
        previous_levels=previous,
        use_switching_cost=False,
    )

    # opzionale: limita durata max (es. 60 minuti)
    plan = opt.decide(horizon_cap_s=3600)
    pprint(plan)
