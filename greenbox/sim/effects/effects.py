from pprint import pformat
from typing import Dict
from pathlib import Path
import pandas as pd


P = Path(__file__).parent.absolute()
EFFECTS_PATH = P / "effects.csv"


class Effects:

    def __init__(self):
        # Load from .csv
        self.df_effects = pd.read_csv(EFFECTS_PATH)
        self.metrics = self.df_effects.drop(
            columns=["system", "level", "energy_consumption", "water_consumption"]
        ).columns.tolist()
        self.systems = sorted(self.df_effects["system"].dropna().unique().tolist())
        self.level = 0

        # first you need to call self.get_system to specify the system
        self.system = None
        self.levels = None
        self.by_level: Dict[str, Dict[str, float]] = None

    def get_system(self, system: str):
        self.system = system
        sys = self.df_effects[self.df_effects["system"] == system]
        self.levels = sys["level"].astype(str).tolist()
        self.by_level: Dict[str, Dict[str, float]] = {
            str(r["level"]): r.drop(labels=["system", "level"]).dropna().to_dict()
            for _, r in sys.iterrows()
        }

    def row_for(self, level: int) -> Dict[str, float]:
        k = f"{int(level)}%"
        row = self.by_level.get(k, self.by_level.get(str(int(level)), {}))
        return {k: float(v) for k, v in row.items() if v is not None}

    def __str__(self):
        return pformat(self.__dict__, indent=1, sort_dicts=False)
