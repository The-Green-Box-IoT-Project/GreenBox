from dataclasses import dataclass
from typing import Tuple


@dataclass
class Threshold:
    """Classe di supporto per rappresentare una soglia con un limite inferiore e uno superiore."""

    lower: float
    upper: float

    @property
    def center(self) -> float:
        return (self.lower + self.upper) / 2

    def band(self) -> Tuple[float, float]:
        return self.lower, self.upper

    def in_band(self, value: float) -> bool:
        return self.lower <= value <= self.upper
