from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True)
class EnvironmentSeries:
    """附件1边界序列；附件区间内仅作分段线性插值。"""

    time_s: np.ndarray
    temperature_c: np.ndarray
    moisture: np.ndarray

    def __post_init__(self) -> None:
        time = np.asarray(self.time_s, dtype=float)
        temperature = np.asarray(self.temperature_c, dtype=float)
        moisture = np.asarray(self.moisture, dtype=float)
        if not (time.ndim == temperature.ndim == moisture.ndim == 1):
            raise ValueError("environment arrays must be one-dimensional")
        if len(time) < 2 or not (len(time) == len(temperature) == len(moisture)):
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

    def values_at(self, t_s: float) -> tuple[float, float]:
        if t_s < self.time_s[0] or t_s > self.time_s[-1]:
            raise ValueError("interpolation time is outside the attachment interval")
        return (
            float(np.interp(t_s, self.time_s, self.temperature_c)),
            float(np.interp(t_s, self.time_s, self.moisture)),
        )


@dataclass(frozen=True)
class PostBoundary:
    temperature_c: float
    moisture: float


def post_boundary_from_tail(
    environment: EnvironmentSeries,
    averaging_window_s: float | None = None,
) -> PostBoundary:
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
    return PostBoundary(
        float(np.trapezoid(temperature, times) / duration),
        float(np.trapezoid(moisture, times) / duration),
    )


def boundary_at(
    t_s: float,
    environment: EnvironmentSeries,
    post_boundary: PostBoundary,
) -> tuple[float, float]:
    if t_s <= environment.terminal_time_s:
        return environment.values_at(t_s)
    return post_boundary.temperature_c, post_boundary.moisture
