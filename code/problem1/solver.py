from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True)
class EnvironmentSeries:
    time_s: np.ndarray
    temperature_c: np.ndarray
    moisture: np.ndarray

    def temperature_at(self, t_s: float) -> float:
        return float(np.interp(t_s, self.time_s, self.temperature_c))

    def moisture_at(self, t_s: float) -> float:
        return float(np.interp(t_s, self.time_s, self.moisture))


@dataclass(frozen=True)
class SolverConfig:
    radius_cm: float = 2.0
    dr_cm: float = 0.1
    duration_s: int = 1800
    dt_s: float = 1.0
    initial_temperature_c: float = 28.0
    initial_moisture: float = 2.55
    density_kg_m3: float = 820.0
    heat_capacity_j_kg_k: float = 2600.0
    thermal_conductivity_w_m_k: float = 0.36
    heat_transfer_w_m2_k: float = 25.0
    mass_transfer_m_s: float = 8e-7


@dataclass(frozen=True)
class SimulationResult:
    time_s: np.ndarray
    radius_cm: np.ndarray
    temperature_c: np.ndarray
    moisture: np.ndarray


def build_radial_grid_cm(radius_cm: float, dr_cm: float) -> np.ndarray:
    count = int(round(radius_cm / dr_cm)) + 1
    return np.round(np.linspace(0.0, radius_cm, count), 10)


def moisture_diffusivity(c: np.ndarray) -> np.ndarray:
    return 7e-9 * np.exp(-0.89 * np.maximum(c, 1e-9))


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


def _implicit_radial_step(
    values: np.ndarray,
    diffusivity: np.ndarray,
    dt_s: float,
    dr_m: float,
    radius_m: float,
    boundary_transfer: float,
    boundary_external: float,
) -> np.ndarray:
    n = len(values)
    r = np.arange(n, dtype=float) * dr_m
    lower = np.zeros(n - 1)
    diag = np.ones(n)
    upper = np.zeros(n - 1)
    rhs = values.copy()

    beta0 = diffusivity[0] * dt_s * 4.0 / dr_m**2
    diag[0] = 1.0 + beta0
    upper[0] = -beta0

    for i in range(1, n - 1):
        a = diffusivity[i] * dt_s
        lower[i - 1] = -a * (1.0 / dr_m**2 - 1.0 / (2.0 * r[i] * dr_m))
        diag[i] = 1.0 + a * 2.0 / dr_m**2
        upper[i] = -a * (1.0 / dr_m**2 + 1.0 / (2.0 * r[i] * dr_m))

    dn = diffusivity[-1]
    surface_loss = boundary_transfer * (2.0 / dr_m + 1.0 / radius_m)
    beta_surface = dt_s * (2.0 * dn / dr_m**2 + surface_loss)
    lower[-1] = -dt_s * 2.0 * dn / dr_m**2
    diag[-1] = 1.0 + beta_surface
    rhs[-1] = values[-1] + dt_s * surface_loss * boundary_external

    return _solve_tridiagonal(lower, diag, upper, rhs)


def solve_problem1(environment: EnvironmentSeries, config: SolverConfig | None = None) -> SimulationResult:
    config = config or SolverConfig()
    radius_cm = build_radial_grid_cm(config.radius_cm, config.dr_cm)
    radius_m = radius_cm / 100.0
    dr_m = config.dr_cm / 100.0
    steps = int(round(config.duration_s / config.dt_s))
    time_s = np.arange(steps + 1, dtype=float) * config.dt_s

    temperature = np.empty((steps + 1, len(radius_cm)), dtype=float)
    moisture = np.empty_like(temperature)
    temperature[0, :] = config.initial_temperature_c
    moisture[0, :] = config.initial_moisture

    alpha = config.thermal_conductivity_w_m_k / (
        config.density_kg_m3 * config.heat_capacity_j_kg_k
    )
    thermal_diffusivity = np.full(len(radius_cm), alpha, dtype=float)

    for n in range(steps):
        t_next = time_s[n + 1]
        temperature[n + 1, :] = _implicit_radial_step(
            temperature[n, :],
            thermal_diffusivity,
            config.dt_s,
            dr_m,
            radius_m[-1],
            config.heat_transfer_w_m2_k
            / (config.density_kg_m3 * config.heat_capacity_j_kg_k),
            environment.temperature_at(t_next),
        )
        moisture[n + 1, :] = _implicit_radial_step(
            moisture[n, :],
            moisture_diffusivity(moisture[n, :]),
            config.dt_s,
            dr_m,
            radius_m[-1],
            config.mass_transfer_m_s,
            environment.moisture_at(t_next),
        )
        moisture[n + 1, :] = np.maximum(moisture[n + 1, :], 0.0)

    return SimulationResult(time_s, radius_cm, temperature, moisture)
