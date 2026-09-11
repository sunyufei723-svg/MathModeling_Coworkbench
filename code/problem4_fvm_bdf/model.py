from __future__ import annotations

import numpy as np


def safe_moisture(c: np.ndarray | float) -> np.ndarray:
    """只在物性公式中使用的数值保护，不修改求解状态。"""

    return np.maximum(np.asarray(c, dtype=float), 1.0e-9)


def density(c: np.ndarray | float) -> np.ndarray:
    c_safe = safe_moisture(c)
    return 760.0 + 90.0 * c_safe


def heat_capacity(c: np.ndarray | float) -> np.ndarray:
    c_safe = safe_moisture(c)
    return 1850.0 + 2150.0 * c_safe / (1.0 + c_safe)


def thermal_conductivity(c: np.ndarray | float) -> np.ndarray:
    c_safe = safe_moisture(c)
    return 0.12 + 0.20 * c_safe / (1.0 + c_safe)


def moisture_diffusivity(
    c: np.ndarray | float,
    temperature_c: np.ndarray | float,
) -> np.ndarray:
    c_safe = safe_moisture(c)
    temperature_k = np.asarray(temperature_c, dtype=float) + 273.15
    if np.any(temperature_k <= 0.0):
        raise ValueError("temperature must be above absolute zero")
    return 4.2e-4 * np.exp(-0.30 / c_safe) * np.exp(-3850.0 / temperature_k)
