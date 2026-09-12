from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True)
class PhysicalParameters:
    """附录4物性及收缩幅度的可注入参数；默认值严格保持原模型口径。"""

    density_intercept: float = 760.0
    density_moisture_coefficient: float = 90.0
    diffusivity_prefactor: float = 4.2e-4
    diffusivity_moisture_parameter: float = 0.30
    activation_temperature_k: float = 3850.0
    shrinkage_amplitude_factor: float = 1.0

    def __post_init__(self) -> None:
        values = np.asarray(
            [
                self.density_intercept,
                self.density_moisture_coefficient,
                self.diffusivity_prefactor,
                self.diffusivity_moisture_parameter,
                self.activation_temperature_k,
                self.shrinkage_amplitude_factor,
            ],
            dtype=float,
        )
        if not np.isfinite(values).all() or np.any(values <= 0.0):
            raise ValueError("physical parameters must be positive and finite")


def safe_moisture(c: np.ndarray | float) -> np.ndarray:
    """只在物性公式中使用的数值保护，不修改求解状态。"""

    return np.maximum(np.asarray(c, dtype=float), 1.0e-9)


def density(
    c: np.ndarray | float,
    parameters: PhysicalParameters | None = None,
) -> np.ndarray:
    parameters = parameters or PhysicalParameters()
    c_safe = safe_moisture(c)
    return parameters.density_intercept + parameters.density_moisture_coefficient * c_safe


def heat_capacity(c: np.ndarray | float) -> np.ndarray:
    c_safe = safe_moisture(c)
    return 1850.0 + 2150.0 * c_safe / (1.0 + c_safe)


def thermal_conductivity(c: np.ndarray | float) -> np.ndarray:
    c_safe = safe_moisture(c)
    return 0.12 + 0.20 * c_safe / (1.0 + c_safe)


def moisture_diffusivity(
    c: np.ndarray | float,
    temperature_c: np.ndarray | float,
    parameters: PhysicalParameters | None = None,
) -> np.ndarray:
    parameters = parameters or PhysicalParameters()
    c_safe = safe_moisture(c)
    temperature_k = np.asarray(temperature_c, dtype=float) + 273.15
    if np.any(temperature_k <= 0.0):
        raise ValueError("temperature must be above absolute zero")
    return (
        parameters.diffusivity_prefactor
        * np.exp(-parameters.diffusivity_moisture_parameter / c_safe)
        * np.exp(-parameters.activation_temperature_k / temperature_k)
    )
