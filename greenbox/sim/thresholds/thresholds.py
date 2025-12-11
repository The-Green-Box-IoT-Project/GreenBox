from dataclasses import dataclass
from typing import Tuple


@dataclass(frozen=True)
class Threshold:
    """A data structure representing the ideal range for a given metric."""
    lower: float
    upper: float
    deadband: float

    @property
    def center(self) -> float:
        """Calculates the center of the main band."""
        return 0.5 * (self.lower + self.upper)

    def band(self) -> Tuple[float, float]:
        """Calculates the operational band, including the deadband."""
        lo = self.lower + self.deadband
        hi = self.upper - self.deadband
        return (lo, hi) if lo <= hi else (self.lower, self.upper)

    def in_band(self, x: float) -> bool:
        """Checks if a value `x` is within the operational band."""
        lo, hi = self.band()
        return lo <= x <= hi