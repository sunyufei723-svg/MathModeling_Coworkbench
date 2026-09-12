from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
from scipy.interpolate import PchipInterpolator


@dataclass(frozen=True)
class RadiusSeries:
    """附件2半径序列，默认线性插值，可切换单调 PCHIP。"""

    time_s: np.ndarray
    radius_cm: np.ndarray
    interpolation: str = "linear"
    _pchip: PchipInterpolator | None = field(default=None, init=False, repr=False, compare=False)

    def __post_init__(self) -> None:
        time = np.asarray(self.time_s, dtype=float)
        radius = np.asarray(self.radius_cm, dtype=float)
        if time.ndim != 1 or radius.ndim != 1 or len(time) != len(radius) or len(time) < 2:
            raise ValueError("radius arrays must be one-dimensional with equal length >= 2")
        if np.any(np.diff(time) <= 0.0):
            raise ValueError("radius time must be strictly increasing")
        if np.any(radius <= 0.0) or not (np.isfinite(time).all() and np.isfinite(radius).all()):
            raise ValueError("radius data must be positive and finite")
        if self.interpolation not in {"linear", "pchip"}:
            raise ValueError("interpolation must be 'linear' or 'pchip'")
        object.__setattr__(self, "time_s", time)
        object.__setattr__(self, "radius_cm", radius)
        if self.interpolation == "pchip":
            object.__setattr__(self, "_pchip", PchipInterpolator(time, radius, extrapolate=False))

    @property
    def terminal_time_s(self) -> float:
        return float(self.time_s[-1])

    def radius_cm_at(self, t_s: float) -> float:
        if t_s <= self.time_s[0]:
            return float(self.radius_cm[0])
        if t_s >= self.time_s[-1]:
            return float(self.radius_cm[-1])
        if self.interpolation == "linear":
            return float(np.interp(t_s, self.time_s, self.radius_cm))
        assert self._pchip is not None
        return float(self._pchip(t_s))

    def radius_rate_cm_s_at(self, t_s: float) -> float:
        if t_s <= self.time_s[0] or t_s >= self.time_s[-1]:
            return 0.0
        if self.interpolation == "linear":
            index = int(np.searchsorted(self.time_s, t_s, side="right") - 1)
            index = min(max(index, 0), len(self.time_s) - 2)
            return float(
                (self.radius_cm[index + 1] - self.radius_cm[index])
                / (self.time_s[index + 1] - self.time_s[index])
            )
        assert self._pchip is not None
        return float(self._pchip.derivative()(t_s))

    def with_interpolation(self, interpolation: str) -> "RadiusSeries":
        return RadiusSeries(self.time_s, self.radius_cm, interpolation)
