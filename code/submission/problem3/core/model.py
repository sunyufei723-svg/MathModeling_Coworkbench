from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True)
class EnvironmentSeries:
    """附件1给出的炉内边界序列；附件区间内只做分段线性插值。"""

    time_s: np.ndarray
    temperature_c: np.ndarray
    moisture: np.ndarray

    def __post_init__(self) -> None:
        time = np.asarray(self.time_s, dtype=float)
        temperature = np.asarray(self.temperature_c, dtype=float)
        moisture = np.asarray(self.moisture, dtype=float)
        if not (time.ndim == temperature.ndim == moisture.ndim == 1):
            raise ValueError("environment arrays must be one-dimensional")
        if not (len(time) == len(temperature) == len(moisture)) or len(time) < 2:
            raise ValueError("environment arrays must have equal length >= 2")
        if np.any(np.diff(time) <= 0.0):
            raise ValueError("environment time must be strictly increasing")
        if not (np.isfinite(time).all() and np.isfinite(temperature).all() and np.isfinite(moisture).all()):
            raise ValueError("environment arrays must be finite")
        object.__setattr__(self, "time_s", time)
        object.__setattr__(self, "temperature_c", temperature)
        object.__setattr__(self, "moisture", moisture)

    @property
    def terminal_time_s(self) -> float:
        return float(self.time_s[-1])

    @property
    def terminal_temperature_c(self) -> float:
        return float(self.temperature_c[-1])

    @property
    def terminal_moisture(self) -> float:
        return float(self.moisture[-1])

    def interpolated_temperature(self, t_s: float) -> float:
        if t_s < self.time_s[0] or t_s > self.time_s[-1]:
            raise ValueError("interpolation time is outside the attachment interval")
        return float(np.interp(t_s, self.time_s, self.temperature_c))

    def interpolated_moisture(self, t_s: float) -> float:
        if t_s < self.time_s[0] or t_s > self.time_s[-1]:
            raise ValueError("interpolation time is outside the attachment interval")
        return float(np.interp(t_s, self.time_s, self.moisture))


@dataclass(frozen=True)
class PostBoundary:
    temperature_c: float
    moisture: float


def _safe_moisture(c: np.ndarray | float) -> np.ndarray:
    """只供物性计算使用；不修改求解器中的状态。"""

    return np.maximum(np.asarray(c, dtype=float), 1e-9)


def density(c: np.ndarray | float) -> np.ndarray:
    safe_c = _safe_moisture(c)
    return 650.0 + 128.0 * safe_c


def heat_capacity(c: np.ndarray | float) -> np.ndarray:
    safe_c = _safe_moisture(c)
    return 1450.0 + 2736.0 * safe_c / (safe_c + 1.0)


def thermal_conductivity(c: np.ndarray | float) -> np.ndarray:
    safe_c = _safe_moisture(c)
    return 0.21 + 0.38 * safe_c / (safe_c + 1.0)


def moisture_diffusivity(c: np.ndarray | float, temperature_c: np.ndarray | float) -> np.ndarray:
    safe_c = _safe_moisture(c)
    temperature_k = np.asarray(temperature_c, dtype=float) + 273.15
    if np.any(temperature_k <= 0.0):
        raise ValueError("temperature must be above absolute zero")
    return 2.4e-3 * np.exp(-0.45 / safe_c) * np.exp(-3850.0 / temperature_k)


def post_boundary_from_tail(environment: EnvironmentSeries, averaging_window_s: float | None = None) -> PostBoundary:
    if averaging_window_s is None:
        return PostBoundary(environment.terminal_temperature_c, environment.terminal_moisture)
    if averaging_window_s <= 0.0:
        raise ValueError("averaging_window_s must be positive")
    start = max(float(environment.time_s[0]), environment.terminal_time_s - averaging_window_s)
    interior = environment.time_s[(environment.time_s > start) & (environment.time_s <= environment.terminal_time_s)]
    times = np.concatenate([[start], interior])
    temperature = np.interp(times, environment.time_s, environment.temperature_c)
    moisture = np.interp(times, environment.time_s, environment.moisture)
    duration = float(times[-1] - times[0])
    if duration <= 0.0:
        raise ValueError("averaging window has zero duration")
    temperature_integral = float(np.sum(0.5 * (temperature[:-1] + temperature[1:]) * np.diff(times)))
    moisture_integral = float(np.sum(0.5 * (moisture[:-1] + moisture[1:]) * np.diff(times)))
    return PostBoundary(
        temperature_integral / duration,
        moisture_integral / duration,
    )
