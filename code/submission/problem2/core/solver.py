from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from scipy.integrate import solve_ivp
from scipy.sparse import bmat, csc_matrix, diags


@dataclass(frozen=True)
class EnvironmentSeries:
    """Piecewise-linear oven temperature and moisture boundary data."""

    time_s: np.ndarray
    temperature_c: np.ndarray
    moisture: np.ndarray

    def __post_init__(self) -> None:
        sizes = {len(self.time_s), len(self.temperature_c), len(self.moisture)}
        if len(sizes) != 1 or not len(self.time_s):
            raise ValueError("environment arrays must have the same non-zero length")
        if np.any(np.diff(self.time_s) <= 0):
            raise ValueError("environment times must be strictly increasing")
        if not (
            np.isfinite(self.time_s).all()
            and np.isfinite(self.temperature_c).all()
            and np.isfinite(self.moisture).all()
        ):
            raise ValueError("environment arrays must be finite")

    def temperature_at(self, t_s: float) -> float:
        return float(np.interp(t_s, self.time_s, self.temperature_c))

    def moisture_at(self, t_s: float) -> float:
        return float(np.interp(t_s, self.time_s, self.moisture))


@dataclass(frozen=True)
class SolverConfig:
    radius_cm: float = 2.0
    internal_dr_cm: float = 0.025
    output_dr_cm: float = 0.1
    duration_s: int = 10800
    output_dt_s: float = 1.0
    initial_temperature_c: float = 28.0
    initial_moisture: float = 2.55
    heat_transfer_w_m2_k: float = 25.0
    mass_transfer_m_s: float = 8e-7
    relative_tolerance: float = 2e-8
    temperature_absolute_tolerance: float = 2e-9
    moisture_absolute_tolerance: float = 2e-10
    max_time_step_s: float = 5.0


@dataclass(frozen=True)
class SolverDiagnostics:
    internal_node_count: int
    state_size: int
    function_evaluations: int
    jacobian_evaluations: int
    lu_decompositions: int
    minimum_temperature_c: float
    minimum_moisture: float


@dataclass(frozen=True)
class SimulationResult:
    time_s: np.ndarray
    radius_cm: np.ndarray
    temperature_c: np.ndarray
    moisture: np.ndarray
    diagnostics: SolverDiagnostics


def build_radial_grid_cm(radius_cm: float, dr_cm: float) -> np.ndarray:
    count = int(round(radius_cm / dr_cm)) + 1
    if count < 2 or not np.isclose(radius_cm / dr_cm, count - 1):
        raise ValueError("radius_cm must be an integer multiple of dr_cm")
    return np.linspace(0.0, radius_cm, count)


def density(c: np.ndarray) -> np.ndarray:
    return 650.0 + 128.0 * np.asarray(c, dtype=float)


def heat_capacity(c: np.ndarray) -> np.ndarray:
    c = np.asarray(c, dtype=float)
    return 1450.0 + 2736.0 * c / (c + 1.0)


def thermal_conductivity(c: np.ndarray) -> np.ndarray:
    c = np.asarray(c, dtype=float)
    return 0.21 + 0.38 * c / (c + 1.0)


def moisture_diffusivity(c: np.ndarray, temperature_c: np.ndarray) -> np.ndarray:
    safe_c = np.maximum(np.asarray(c, dtype=float), 1e-9)
    temperature_k = np.asarray(temperature_c, dtype=float) + 273.15
    if np.any(temperature_k <= 0.0):
        raise ValueError("temperature must be above absolute zero")
    return 2.4e-3 * np.exp(-0.45 / safe_c) * np.exp(-3850.0 / temperature_k)


def harmonic_mean(left: np.ndarray, right: np.ndarray) -> np.ndarray:
    left = np.asarray(left, dtype=float)
    right = np.asarray(right, dtype=float)
    denominator = left + right
    result = np.zeros_like(denominator)
    np.divide(2.0 * left * right, denominator, out=result, where=denominator > 0.0)
    return result


def radial_geometry(radius_m: float, dr_m: float) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    node_count = int(round(radius_m / dr_m)) + 1
    radius = np.linspace(0.0, radius_m, node_count)
    left_faces = np.maximum(0.0, radius - dr_m / 2.0)
    right_faces = np.minimum(radius_m, radius + dr_m / 2.0)
    volumes = np.pi * (right_faces**2 - left_faces**2)
    interface_areas = 2.0 * np.pi * (radius[:-1] + dr_m / 2.0)
    return radius, volumes, interface_areas


def add_internal_fluxes(
    derivative_numerator: np.ndarray,
    values: np.ndarray,
    interface_transport: np.ndarray,
    interface_areas: np.ndarray,
    dr_m: float,
) -> None:
    flux = interface_transport * interface_areas * (values[1:] - values[:-1]) / dr_m
    derivative_numerator[:-1] += flux
    derivative_numerator[1:] -= flux


def build_coupled_jacobian_sparsity(node_count: int) -> csc_matrix:
    """Four nearest-neighbour sparse blocks for [T_0..T_N, C_0..C_N]."""

    tri = diags(
        [np.ones(node_count - 1), np.ones(node_count), np.ones(node_count - 1)],
        offsets=[-1, 0, 1],
        shape=(node_count, node_count),
        format="csc",
    )
    return bmat([[tri, tri], [tri, tri]], format="csc")


def sample_to_output_grid(
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


def solve_problem2(
    environment: EnvironmentSeries,
    config: SolverConfig | None = None,
) -> SimulationResult:
    """Solve the nonlinear T/C system by conservative radial FVM and adaptive BDF."""

    config = config or SolverConfig()
    if environment.time_s[0] > 0.0 or environment.time_s[-1] < config.duration_s:
        raise ValueError("environment data must cover the complete simulation interval")

    internal_radius_cm = build_radial_grid_cm(config.radius_cm, config.internal_dr_cm)
    output_radius_cm = build_radial_grid_cm(config.radius_cm, config.output_dr_cm)
    dr_m = config.internal_dr_cm / 100.0
    radius_m = config.radius_cm / 100.0
    _, volumes, interface_areas = radial_geometry(radius_m, dr_m)
    surface_area = 2.0 * np.pi * radius_m
    node_count = len(internal_radius_cm)
    jacobian_pattern = build_coupled_jacobian_sparsity(node_count)
    output_time_s = np.arange(
        0.0,
        config.duration_s + config.output_dt_s / 2.0,
        config.output_dt_s,
    )

    def coupled_rhs(t_s: float, state: np.ndarray) -> np.ndarray:
        temperature = state[:node_count]
        moisture = state[node_count:]
        safe_moisture = np.maximum(moisture, 1e-9)

        rho_cp = density(safe_moisture) * heat_capacity(safe_moisture)
        node_k = thermal_conductivity(safe_moisture)
        node_d = moisture_diffusivity(safe_moisture, temperature)
        face_k = harmonic_mean(node_k[:-1], node_k[1:])
        face_d = harmonic_mean(node_d[:-1], node_d[1:])

        heat_numerator = np.zeros(node_count, dtype=float)
        moisture_numerator = np.zeros(node_count, dtype=float)
        add_internal_fluxes(
            heat_numerator,
            temperature,
            face_k,
            interface_areas,
            dr_m,
        )
        add_internal_fluxes(
            moisture_numerator,
            moisture,
            face_d,
            interface_areas,
            dr_m,
        )

        heat_numerator[-1] += (
            config.heat_transfer_w_m2_k
            * surface_area
            * (environment.temperature_at(t_s) - temperature[-1])
        )
        moisture_numerator[-1] += (
            config.mass_transfer_m_s
            * surface_area
            * (environment.moisture_at(t_s) - moisture[-1])
        )

        temperature_rate = heat_numerator / (rho_cp * volumes)
        moisture_rate = moisture_numerator / volumes
        return np.concatenate([temperature_rate, moisture_rate])

    initial_state = np.concatenate(
        [
            np.full(node_count, config.initial_temperature_c),
            np.full(node_count, config.initial_moisture),
        ]
    )
    absolute_tolerance = np.concatenate(
        [
            np.full(node_count, config.temperature_absolute_tolerance),
            np.full(node_count, config.moisture_absolute_tolerance),
        ]
    )
    solution = solve_ivp(
        coupled_rhs,
        (0.0, float(config.duration_s)),
        initial_state,
        method="BDF",
        t_eval=output_time_s,
        rtol=config.relative_tolerance,
        atol=absolute_tolerance,
        max_step=config.max_time_step_s,
        jac_sparsity=jacobian_pattern,
    )
    if not solution.success:
        raise RuntimeError(f"coupled integration failed: {solution.message}")
    if not np.isfinite(solution.y).all():
        raise RuntimeError("coupled integration returned non-finite values")

    internal_temperature = solution.y[:node_count, :].T
    internal_moisture = solution.y[node_count:, :].T
    if float(internal_moisture.min()) < -1e-8:
        raise RuntimeError("coupled integration returned materially negative moisture")

    temperature = sample_to_output_grid(
        internal_radius_cm,
        output_radius_cm,
        internal_temperature,
    )
    moisture = sample_to_output_grid(
        internal_radius_cm,
        output_radius_cm,
        internal_moisture,
    )
    diagnostics = SolverDiagnostics(
        internal_node_count=node_count,
        state_size=2 * node_count,
        function_evaluations=int(solution.nfev),
        jacobian_evaluations=int(solution.njev),
        lu_decompositions=int(solution.nlu),
        minimum_temperature_c=float(internal_temperature.min()),
        minimum_moisture=float(internal_moisture.min()),
    )
    return SimulationResult(output_time_s, output_radius_cm, temperature, moisture, diagnostics)
