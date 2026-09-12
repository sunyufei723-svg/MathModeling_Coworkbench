"""problem1 改进版求解器（独立目录，不改动 code/problem1/ 原文件）。

在 agent_C 的原版 problem1（守恒径向 FVM + 隐式 BDF）基础上，实现两处「可选改进」：

改进①（界面扩散系数谐波平均）：原版 moisture_rhs 用算术平均
    ``0.5*(D[i]+D[i+1])`` 计算控制体积界面的扩散系数。干燥前沿处 D(C)=7e-9·exp(-0.89/C)
    随 C 跨数量级变化时，算术平均会系统性高估界面通量；改用谐波平均
    ``2*D[i]*D[i+1]/(D[i]+D[i+1])``（Patankar《Numerical Heat Transfer》标准做法），
    对串联扩散阻力的刻画更准确。

改进②（表面强脱水 C≥0 裁剪）：显式/半隐式推进在表面强脱水时可能出现非物理的
    负水分浓度；在输出前对水分场做 ``max(C, 0)`` 裁剪。注意 problem1 的 30 min 工况
    表面水分最低约 1.51 kg/kg，远不到 0，此裁剪在本问实际是 no-op，属防御性改进
    （为问3/问4 等更长、更强脱水工况兜底）。

为便于「改进 vs 基线」做纯粹对比，SolverConfig 保留可切换开关：
    interface_mean="arithmetic" + clip_negative_moisture=False 即退化为原版行为。

温度场与水分场在 problem1 中解耦（温度用常物性 k、界面 transport 为常数，不涉及
平均方式），故两处改进只影响水分场，温度场与原版逐点一致。
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from scipy.integrate import solve_ivp
from scipy.sparse import diags


@dataclass(frozen=True)
class EnvironmentSeries:
    """Piecewise-linear oven boundary data."""

    time_s: np.ndarray
    temperature_c: np.ndarray
    moisture: np.ndarray

    def __post_init__(self) -> None:
        sizes = {len(self.time_s), len(self.temperature_c), len(self.moisture)}
        if len(sizes) != 1 or not len(self.time_s):
            raise ValueError("environment arrays must have the same non-zero length")
        if np.any(np.diff(self.time_s) <= 0):
            raise ValueError("environment times must be strictly increasing")

    def temperature_at(self, t_s: float) -> float:
        return float(np.interp(t_s, self.time_s, self.temperature_c))

    def moisture_at(self, t_s: float) -> float:
        return float(np.interp(t_s, self.time_s, self.moisture))


@dataclass(frozen=True)
class SolverConfig:
    radius_cm: float = 2.0
    internal_dr_cm: float = 0.0025
    output_dr_cm: float = 0.1
    duration_s: int = 1800
    output_dt_s: float = 1.0
    initial_temperature_c: float = 28.0
    initial_moisture: float = 2.55
    density_kg_m3: float = 820.0
    heat_capacity_j_kg_k: float = 2600.0
    thermal_conductivity_w_m_k: float = 0.36
    heat_transfer_w_m2_k: float = 25.0
    mass_transfer_m_s: float = 8e-7
    relative_tolerance: float = 1e-7
    absolute_tolerance: float = 1e-9
    max_time_step_s: float = 10.0
    # --- 改进开关（默认=改进版行为）---
    interface_mean: str = "harmonic"          # "harmonic"（改进①）| "arithmetic"（原版基线）
    clip_negative_moisture: bool = True       # True（改进②）| False（原版基线）


@dataclass(frozen=True)
class SimulationResult:
    time_s: np.ndarray
    radius_cm: np.ndarray
    temperature_c: np.ndarray
    moisture: np.ndarray


def build_radial_grid_cm(radius_cm: float, dr_cm: float) -> np.ndarray:
    count = int(round(radius_cm / dr_cm)) + 1
    if count < 2 or not np.isclose(radius_cm / dr_cm, count - 1):
        raise ValueError("radius_cm must be an integer multiple of dr_cm")
    return np.linspace(0.0, radius_cm, count)


def moisture_diffusivity(c: np.ndarray) -> np.ndarray:
    """Problem-1 diffusivity, D(C)=7e-9 exp(-0.89/C), in m²/s."""

    safe_c = np.maximum(np.asarray(c, dtype=float), 1e-12)
    return 7e-9 * np.exp(-0.89 / safe_c)


def interface_average(d_left: np.ndarray, d_right: np.ndarray, kind: str) -> np.ndarray:
    """控制体积界面扩散系数平均。

    kind="arithmetic"：0.5*(D_l+D_r)（原版）。
    kind="harmonic"：2*D_l*D_r/(D_l+D_r)（改进①）；对 D 跨数量级的串联扩散更准，
        且当任一侧 D→0（表面强脱水）时界面 D→0，比算术平均更物理。防 0/0：分母为 0 时取 0。
    """

    if kind == "arithmetic":
        return 0.5 * (d_left + d_right)
    if kind != "harmonic":
        raise ValueError(f"unknown interface_mean: {kind!r} (expected 'harmonic' or 'arithmetic')")
    denom = d_left + d_right
    safe = np.where(denom > 0.0, denom, 1.0)
    return np.where(denom > 0.0, 2.0 * d_left * d_right / safe, 0.0)


def _radial_geometry(radius_m: float, dr_m: float) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    node_count = int(round(radius_m / dr_m)) + 1
    radius = np.linspace(0.0, radius_m, node_count)
    left_faces = np.maximum(0.0, radius - dr_m / 2.0)
    right_faces = np.minimum(radius_m, radius + dr_m / 2.0)
    volumes = np.pi * (right_faces**2 - left_faces**2)
    interface_areas = 2.0 * np.pi * (radius[:-1] + dr_m / 2.0)
    return radius, volumes, interface_areas


def _add_internal_fluxes(
    derivative_numerator: np.ndarray,
    values: np.ndarray,
    interface_transport: np.ndarray,
    interface_areas: np.ndarray,
    dr_m: float,
) -> None:
    flux = interface_transport * interface_areas * (values[1:] - values[:-1]) / dr_m
    derivative_numerator[:-1] += flux
    derivative_numerator[1:] -= flux


def _sample_to_output_grid(
    internal_radius_cm: np.ndarray,
    output_radius_cm: np.ndarray,
    states_by_time: np.ndarray,
) -> np.ndarray:
    spacing_cm = internal_radius_cm[1] - internal_radius_cm[0]
    indices = np.rint(output_radius_cm / spacing_cm).astype(int)
    if np.allclose(internal_radius_cm[indices], output_radius_cm):
        return states_by_time[:, indices]
    return np.vstack(
        [np.interp(output_radius_cm, internal_radius_cm, row) for row in states_by_time]
    )


def solve_problem1(environment: EnvironmentSeries, config: SolverConfig | None = None) -> SimulationResult:
    """Solve the decoupled heat/moisture model by radial FVM + implicit BDF."""

    config = config or SolverConfig()
    internal_radius_cm = build_radial_grid_cm(config.radius_cm, config.internal_dr_cm)
    output_radius_cm = build_radial_grid_cm(config.radius_cm, config.output_dr_cm)
    dr_m = config.internal_dr_cm / 100.0
    radius_m = config.radius_cm / 100.0
    _, volumes, interface_areas = _radial_geometry(radius_m, dr_m)
    surface_area = 2.0 * np.pi * radius_m
    node_count = len(internal_radius_cm)
    jacobian_pattern = diags(
        [np.ones(node_count - 1), np.ones(node_count), np.ones(node_count - 1)],
        offsets=[-1, 0, 1],
        shape=(node_count, node_count),
        format="csc",
    )
    output_time_s = np.arange(
        0.0,
        config.duration_s + config.output_dt_s / 2.0,
        config.output_dt_s,
    )

    def temperature_rhs(t_s: float, temperature: np.ndarray) -> np.ndarray:
        numerator = np.zeros_like(temperature)
        _add_internal_fluxes(
            numerator,
            temperature,
            np.full(node_count - 1, config.thermal_conductivity_w_m_k),
            interface_areas,
            dr_m,
        )
        numerator[-1] += (
            config.heat_transfer_w_m2_k
            * surface_area
            * (environment.temperature_at(t_s) - temperature[-1])
        )
        return numerator / (config.density_kg_m3 * config.heat_capacity_j_kg_k * volumes)

    def moisture_rhs(t_s: float, moisture: np.ndarray) -> np.ndarray:
        numerator = np.zeros_like(moisture)
        node_diffusivity = moisture_diffusivity(moisture)
        # 改进①：界面 D 用谐波平均（config.interface_mean="arithmetic" 时退化为原版算术平均）
        interface_diffusivity = interface_average(
            node_diffusivity[:-1], node_diffusivity[1:], config.interface_mean
        )
        _add_internal_fluxes(
            numerator,
            moisture,
            interface_diffusivity,
            interface_areas,
            dr_m,
        )
        numerator[-1] += (
            config.mass_transfer_m_s
            * surface_area
            * (environment.moisture_at(t_s) - moisture[-1])
        )
        return numerator / volumes

    common_options = {
        "method": "BDF",
        "t_eval": output_time_s,
        "rtol": config.relative_tolerance,
        "atol": config.absolute_tolerance,
        "max_step": config.max_time_step_s,
        "jac_sparsity": jacobian_pattern,
    }
    temperature_solution = solve_ivp(
        temperature_rhs,
        (0.0, float(config.duration_s)),
        np.full(node_count, config.initial_temperature_c),
        **common_options,
    )
    moisture_solution = solve_ivp(
        moisture_rhs,
        (0.0, float(config.duration_s)),
        np.full(node_count, config.initial_moisture),
        **common_options,
    )
    if not temperature_solution.success:
        raise RuntimeError(f"temperature integration failed: {temperature_solution.message}")
    if not moisture_solution.success:
        raise RuntimeError(f"moisture integration failed: {moisture_solution.message}")

    temperature = _sample_to_output_grid(
        internal_radius_cm,
        output_radius_cm,
        temperature_solution.y.T,
    )
    moisture = _sample_to_output_grid(
        internal_radius_cm,
        output_radius_cm,
        moisture_solution.y.T,
    )
    # 改进②：表面强脱水可能出现非物理负水分，输出前裁剪到 C≥0（problem1 工况实测不触发，防御性）
    if config.clip_negative_moisture:
        moisture = np.maximum(moisture, 0.0)
    return SimulationResult(output_time_s, output_radius_cm, temperature, moisture)
