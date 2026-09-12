from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True)
class EnvironmentSeries:
    """烘房温湿边界（附件1）；超出数据范围按末值保持（np.interp 自动 clamp）。"""

    time_s: np.ndarray
    temperature_c: np.ndarray
    moisture: np.ndarray

    def temperature_at(self, t_s: float) -> float:
        return float(np.interp(t_s, self.time_s, self.temperature_c))

    def moisture_at(self, t_s: float) -> float:
        return float(np.interp(t_s, self.time_s, self.moisture))


@dataclass(frozen=True)
class RadiusSeries:
    """药材半径随时间收缩的经验数据（附件2）；t>末点取末值（np.interp clamp）。"""

    time_s: np.ndarray
    radius_cm: np.ndarray

    def radius_cm_at(self, t_s: float) -> float:
        return float(np.interp(t_s, self.time_s, self.radius_cm))


@dataclass(frozen=True)
class SolverConfig:
    xi_points: int = 101                 # ξ∈[0,1] 固定计算网格点数（front-fixing）
    duration_limit_s: int = 259200       # 72 h，与附件2 覆盖范围一致
    dt_s: float = 10.0
    output_interval_s: int = 60
    initial_temperature_c: float = 28.0
    initial_moisture: float = 2.55
    completion_threshold: float = 0.15
    heat_transfer_w_m2_k: float = 25.0
    mass_transfer_m_s: float = 8e-7
    max_coupling_iterations: int = 8
    coupling_tolerance: float = 1e-8


@dataclass(frozen=True)
class SimulationResult:
    time_s: np.ndarray                   # 采样时刻
    xi: np.ndarray                       # 固定 ξ 网格 [0,1]
    radius_cm: np.ndarray                # 各采样时刻的 R(t)/cm
    temperature_c: np.ndarray            # (n_samples, xi_points)，°C
    moisture: np.ndarray                 # (n_samples, xi_points)，kg/kg
    coupling_iterations: np.ndarray
    coupling_converged: np.ndarray
    drying_end_time_s: int


# ---------------------------------------------------------------------------
# 附录4 物性经验公式（问题4 专用；均随 C 变，D 依赖 T(K)）
# ---------------------------------------------------------------------------
def density(c: np.ndarray) -> np.ndarray:
    return 760.0 + 90.0 * c


def heat_capacity(c: np.ndarray) -> np.ndarray:
    return 1850.0 + 2150.0 * c / (c + 1.0)


def thermal_conductivity(c: np.ndarray) -> np.ndarray:
    return 0.12 + 0.20 * c / (c + 1.0)


def moisture_diffusivity(c: np.ndarray, temperature_c: np.ndarray) -> np.ndarray:
    safe_c = np.maximum(c, 1e-9)
    temperature_k = temperature_c + 273.15
    return 4.2e-4 * np.exp(-0.30 / safe_c) * np.exp(-3850.0 / temperature_k)


def drying_complete(moisture_profile: np.ndarray, threshold: float = 0.15) -> bool:
    return bool(np.max(moisture_profile) < threshold)


def build_xi_grid(xi_points: int) -> np.ndarray:
    return np.linspace(0.0, 1.0, xi_points)


def build_output_seconds(end_time_s: int, interval_s: int = 60) -> np.ndarray:
    if end_time_s < interval_s:
        return np.array([end_time_s], dtype=int)
    regular = list(range(interval_s, end_time_s + 1, interval_s))
    if regular[-1] != end_time_s:
        regular.append(end_time_s)
    return np.array(regular, dtype=int)


def _solve_tridiagonal(lower: np.ndarray, diag: np.ndarray, upper: np.ndarray, rhs: np.ndarray) -> np.ndarray:
    n = len(diag)
    c_prime = np.zeros(n - 1)
    d_prime = np.zeros(n)

    c_prime[0] = upper[0] / diag[0]
    d_prime[0] = rhs[0] / diag[0]
    for i in range(1, n):
        denom = diag[i] - lower[i - 1] * c_prime[i - 1]
        if i < n - 1:
            c_prime[i] = upper[i] / denom
        d_prime[i] = (rhs[i] - lower[i - 1] * d_prime[i - 1]) / denom

    x = np.zeros(n)
    x[-1] = d_prime[-1]
    for i in range(n - 2, -1, -1):
        x[i] = d_prime[i] - c_prime[i] * x[i + 1]
    return x


def _face_average(values: np.ndarray) -> np.ndarray:
    return 0.5 * (values[:-1] + values[1:])


def _implicit_radial_variable_step(
    values: np.ndarray,
    conductivity: np.ndarray,
    capacity: np.ndarray,
    dt_s: float,
    dr_m: float,
    boundary_transfer: float,
    boundary_external: float,
) -> np.ndarray:
    """守恒径向 FVM 全隐式一步（中心对称消 1/r 奇点、表面第三类 Robin）。

    对问题4：直接复用于 ξ∈[0,1] 单位圆盘，传入 dr_m=dξ（无量纲）、
    conductivity=cond/R²（有效压缩扩散系数）、boundary_transfer=transfer/R，
    即得物质型 front-fixing 的 ξ 系离散（radius_m=(n-1)*dξ=1）。
    """
    n = len(values)
    radius_m = (n - 1) * dr_m
    face = _face_average(conductivity)
    lower = np.zeros(n - 1)
    diag = np.ones(n)
    upper = np.zeros(n - 1)
    rhs = values.copy()

    coef_center = 4.0 * face[0] * dt_s / (capacity[0] * dr_m**2)
    diag[0] = 1.0 + coef_center
    upper[0] = -coef_center

    for i in range(1, n - 1):
        r_i = i * dr_m
        r_minus = r_i - 0.5 * dr_m
        r_plus = r_i + 0.5 * dr_m
        a_minus = dt_s * face[i - 1] * r_minus / (capacity[i] * r_i * dr_m**2)
        a_plus = dt_s * face[i] * r_plus / (capacity[i] * r_i * dr_m**2)
        lower[i - 1] = -a_minus
        diag[i] = 1.0 + a_minus + a_plus
        upper[i] = -a_plus

    surface_conduction = 2.0 * conductivity[-1] * dt_s / (capacity[-1] * dr_m**2)
    surface_exchange = boundary_transfer * dt_s * (2.0 / dr_m + 1.0 / radius_m) / capacity[-1]
    lower[-1] = -surface_conduction
    diag[-1] = 1.0 + surface_conduction + surface_exchange
    rhs[-1] = values[-1] + surface_exchange * boundary_external

    return _solve_tridiagonal(lower, diag, upper, rhs)


def _coupled_step(
    previous_temperature: np.ndarray,
    previous_moisture: np.ndarray,
    environment: EnvironmentSeries,
    radius_cm: float,
    t_next: float,
    config: SolverConfig,
    dxi: float,
) -> tuple[np.ndarray, np.ndarray, int, bool]:
    """单时间步：Picard 联立迭代 T/C；移动边界经 R(t) 的有效系数进入。"""
    radius_m = radius_cm / 100.0
    inv_r2 = 1.0 / (radius_m**2)
    inv_r = 1.0 / radius_m

    t_guess = previous_temperature.copy()
    c_guess = previous_moisture.copy()
    next_temperature = t_guess
    next_moisture = c_guess

    for iteration in range(1, config.max_coupling_iterations + 1):
        c_safe = np.maximum(c_guess, 1e-9)
        rho_cp = density(c_safe) * heat_capacity(c_safe)
        k_eff = thermal_conductivity(c_safe) * inv_r2      # 压缩扩散：k/R²
        d_eff = moisture_diffusivity(c_safe, t_guess) * inv_r2

        next_temperature = _implicit_radial_variable_step(
            previous_temperature,
            k_eff,
            rho_cp,
            config.dt_s,
            dxi,
            config.heat_transfer_w_m2_k * inv_r,           # 表面对流：h/R
            environment.temperature_at(t_next),
        )
        next_moisture = _implicit_radial_variable_step(
            previous_moisture,
            d_eff,
            np.ones_like(d_eff),
            config.dt_s,
            dxi,
            config.mass_transfer_m_s * inv_r,              # 表面对流：hm/R
            environment.moisture_at(t_next),
        )
        next_moisture = np.maximum(next_moisture, 0.0)

        delta_t = np.max(np.abs(next_temperature - t_guess))
        delta_c = np.max(np.abs(next_moisture - c_guess))
        if max(delta_t, delta_c) <= config.coupling_tolerance:
            return next_temperature, next_moisture, iteration, True

        t_guess = next_temperature
        c_guess = next_moisture

    return next_temperature, next_moisture, config.max_coupling_iterations, False


def solve_problem4(
    environment: EnvironmentSeries,
    radius: RadiusSeries,
    config: SolverConfig | None = None,
) -> SimulationResult:
    config = config or SolverConfig()
    xi = build_xi_grid(config.xi_points)
    dxi = 1.0 / (config.xi_points - 1)
    steps = int(round(config.duration_limit_s / config.dt_s))

    current_temperature = np.full(config.xi_points, config.initial_temperature_c, dtype=float)
    current_moisture = np.full(config.xi_points, config.initial_moisture, dtype=float)
    sample_times: list[int] = []
    sample_radius: list[float] = []
    sampled_temperature: list[np.ndarray] = []
    sampled_moisture: list[np.ndarray] = []
    iteration_counts: list[int] = []
    convergence_flags: list[bool] = []
    drying_end_time_s: int | None = None

    for step in range(1, steps + 1):
        t_next = step * config.dt_s
        radius_cm = radius.radius_cm_at(t_next)
        current_temperature, current_moisture, iterations, converged = _coupled_step(
            current_temperature,
            current_moisture,
            environment,
            radius_cm,
            t_next,
            config,
            dxi,
        )
        iteration_counts.append(iterations)
        convergence_flags.append(converged)

        is_regular_output = np.isclose(t_next % config.output_interval_s, 0.0)
        is_complete = drying_complete(current_moisture, config.completion_threshold)
        if is_regular_output or is_complete:
            sample_times.append(int(round(t_next)))
            sample_radius.append(radius_cm)
            sampled_temperature.append(current_temperature.copy())
            sampled_moisture.append(current_moisture.copy())

        if is_complete:
            drying_end_time_s = int(round(t_next))
            break

    if drying_end_time_s is None:
        raise RuntimeError(
            f"在 {config.duration_limit_s} s 内未达到全域水分浓度低于 {config.completion_threshold} kg/kg"
        )

    return SimulationResult(
        np.array(sample_times, dtype=float),
        xi,
        np.array(sample_radius, dtype=float),
        np.vstack(sampled_temperature),
        np.vstack(sampled_moisture),
        np.array(iteration_counts, dtype=int),
        np.array(convergence_flags, dtype=bool),
        drying_end_time_s,
    )
