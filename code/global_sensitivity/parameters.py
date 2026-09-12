from __future__ import annotations

from dataclasses import asdict, dataclass

import numpy as np


@dataclass(frozen=True)
class ParameterSpec:
    name: str
    label: str
    lower: float
    upper: float
    unit: str
    interpretation: str

    def __post_init__(self) -> None:
        if not np.isfinite([self.lower, self.upper]).all() or self.upper <= self.lower:
            raise ValueError(f"invalid range for {self.name}")

    def from_unit(self, value: float) -> float:
        if not np.isfinite(value) or value < -1.0e-12 or value > 1.0 + 1.0e-12:
            raise ValueError(f"normalized {self.name} must lie in [0, 1]")
        clipped = min(max(float(value), 0.0), 1.0)
        return self.lower + clipped * (self.upper - self.lower)


PARAMETER_SPECS: tuple[ParameterSpec, ...] = (
    ParameterSpec(
        "ambient_temperature_delta_c",
        r"$\Delta T_\infty$",
        -2.0,
        2.0,
        "deg C",
        "4 h 后环境温度相对附件末值的工程偏移",
    ),
    ParameterSpec(
        "ambient_moisture_factor",
        r"$f_{C_\infty}$",
        0.9,
        1.1,
        "1",
        "4 h 后环境水分边界倍率",
    ),
    ParameterSpec(
        "heat_transfer_factor",
        r"$f_h$",
        0.9,
        1.1,
        "1",
        "表面对流换热系数倍率",
    ),
    ParameterSpec(
        "mass_transfer_factor",
        r"$f_{h_m}$",
        0.9,
        1.1,
        "1",
        "表面对流传质系数倍率",
    ),
    ParameterSpec(
        "diffusivity_prefactor_factor",
        r"$f_{D_0}$",
        0.9,
        1.1,
        "1",
        "附录4水分扩散前因子倍率",
    ),
    ParameterSpec(
        "activation_temperature_factor",
        r"$f_\beta$",
        0.95,
        1.05,
        "1",
        "活化温度参数 beta=3850 K 的倍率",
    ),
    ParameterSpec(
        "shrinkage_amplitude_factor",
        r"$f_R$",
        0.95,
        1.05,
        "1",
        "保持初始半径不变的收缩幅度倍率",
    ),
    ParameterSpec(
        "density_intercept_factor",
        r"$f_{\rho_0}$",
        0.95,
        1.05,
        "1",
        "密度关系截距760的倍率",
    ),
    ParameterSpec(
        "density_slope_factor",
        r"$f_{\rho_1}$",
        0.9,
        1.1,
        "1",
        "密度关系水分系数90的倍率",
    ),
)


def parameter_names() -> tuple[str, ...]:
    return tuple(item.name for item in PARAMETER_SPECS)


def default_unit_point() -> np.ndarray:
    return np.full(len(PARAMETER_SPECS), 0.5, dtype=float)


def point_from_unit(unit_point: np.ndarray | list[float]) -> dict[str, float]:
    values = np.asarray(unit_point, dtype=float)
    if values.shape != (len(PARAMETER_SPECS),):
        raise ValueError(f"unit point must have shape ({len(PARAMETER_SPECS)},)")
    return {spec.name: spec.from_unit(value) for spec, value in zip(PARAMETER_SPECS, values, strict=True)}


def unit_from_point(point: dict[str, float]) -> np.ndarray:
    values = []
    for spec in PARAMETER_SPECS:
        value = float(point[spec.name])
        unit = (value - spec.lower) / (spec.upper - spec.lower)
        if unit < -1.0e-12 or unit > 1.0 + 1.0e-12:
            raise ValueError(f"{spec.name} is outside its declared range")
        values.append(min(max(unit, 0.0), 1.0))
    return np.asarray(values, dtype=float)


def parameter_metadata() -> list[dict[str, object]]:
    return [asdict(item) for item in PARAMETER_SPECS]
