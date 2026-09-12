from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from scipy.linalg.lapack import dgtsv

try:
    from .environment import EnvironmentSeries, PostBoundary, boundary_at, post_boundary_from_tail
    from .fvm import ReferenceGeometry, build_reference_geometry, interface_values, sample_physical_profile
    from .model import density, heat_capacity, moisture_diffusivity, thermal_conductivity
    from .radius import RadiusSeries
    from .solver_bdf import DEFAULT_FIXED_DISTANCES_CM
except ImportError:
    from environment import EnvironmentSeries, PostBoundary, boundary_at, post_boundary_from_tail  # type: ignore
    from fvm import ReferenceGeometry, build_reference_geometry, interface_values, sample_physical_profile  # type: ignore
    from model import density, heat_capacity, moisture_diffusivity, thermal_conductivity  # type: ignore
    from radius import RadiusSeries  # type: ignore
    from solver_bdf import DEFAULT_FIXED_DISTANCES_CM  # type: ignore


@dataclass(frozen=True)
class BESolverConfig:
    node_count: int = 801
    time_step_s: float = 10.0
    sample_interval_s: int = 21600
    fixed_distances_cm: tuple[float, ...] = DEFAULT_FIXED_DISTANCES_CM
    initial_temperature_c: float = 28.0
    initial_moisture: float = 2.55
    completion_threshold: float = 0.15
    heat_transfer_w_m2_k: float = 25.0
    mass_transfer_m_s: float = 8.0e-7
    k_interface_mean: str = "harmonic"
    d_interface_mean: str = "harmonic"
    fixed_radius_cm: float | None = None
    maximum_picard_iterations: int = 20
    temperature_picard_tolerance: float = 1.0e-8
    moisture_picard_tolerance: float = 1.0e-10
    fallback_time_limit_s: float = 96.0 * 3600.0
    event_bracket_tolerance_s: float = 0.5
    material_negative_tolerance: float = -1.0e-8


@dataclass(frozen=True)
class BEDiagnostics:
    accepted_steps: int
    bisection_steps: int
    maximum_picard_iterations_used: int
    mean_picard_iterations: float
    unconverged_steps: int
    maximum_final_temperature_iteration_error: float
    maximum_final_moisture_iteration_error: float
    minimum_raw_moisture: float


@dataclass(frozen=True)
class BEResult:
    time_s: np.ndarray
    radius_cm: np.ndarray
    fixed_distance_cm: np.ndarray
    temperature_c: np.ndarray
    moisture: np.ndarray
    drying_event_time_s: float
    event_radius_cm: float
    event_temperature_internal: np.ndarray
    event_moisture_internal: np.ndarray
    event_output_temperature: np.ndarray
    event_output_moisture: np.ndarray
    diagnostics: BEDiagnostics


def _solve_tridiagonal(
    lower: np.ndarray,
    diagonal: np.ndarray,
    upper: np.ndarray,
    right_hand_side: np.ndarray,
) -> np.ndarray:
    _, _, _, result, info = dgtsv(
        lower.copy(),
        diagonal.copy(),
        upper.copy(),
        right_hand_side.copy(),
        overwrite_dl=True,
        overwrite_d=True,
        overwrite_du=True,
        overwrite_b=True,
    )
    if info != 0:
        raise RuntimeError(f"compiled TDMA failed with LAPACK info={info}")
    return np.asarray(result, dtype=float)


def _radius_m_at(t_s: float, radius: RadiusSeries, fixed_radius_cm: float | None) -> float:
    if fixed_radius_cm is not None:
        if fixed_radius_cm <= 0.0:
            raise ValueError("fixed_radius_cm must be positive")
        return fixed_radius_cm / 100.0
    return radius.radius_cm_at(t_s) / 100.0


def _implicit_reference_step(
    previous: np.ndarray,
    node_transport: np.ndarray,
    capacity: np.ndarray,
    dt_s: float,
    radius_m: float,
    boundary_transfer: float,
    boundary_external: float,
    geometry: ReferenceGeometry,
    interface_mean: str,
) -> np.ndarray:
    face_transport = interface_values(node_transport, interface_mean)
    conductance = face_transport * geometry.interface_areas_hat / (geometry.dxi * radius_m**2)
    accumulation = capacity * geometry.volumes_hat / dt_s
    lower = -conductance.copy()
    upper = -conductance.copy()
    diagonal = accumulation.copy()
    diagonal[:-1] += conductance
    diagonal[1:] += conductance
    right_hand_side = accumulation * previous
    boundary_conductance = boundary_transfer / radius_m
    diagonal[-1] += boundary_conductance
    right_hand_side[-1] += boundary_conductance * boundary_external
    return _solve_tridiagonal(lower, diagonal, upper, right_hand_side)


def coupled_backward_euler_step(
    previous_temperature: np.ndarray,
    previous_moisture: np.ndarray,
    t_next_s: float,
    dt_s: float,
    geometry: ReferenceGeometry,
    environment: EnvironmentSeries,
    post_boundary: PostBoundary,
    radius: RadiusSeries,
    config: BESolverConfig,
) -> tuple[np.ndarray, np.ndarray, int, float, float]:
    if dt_s <= 0.0:
        raise ValueError("dt_s must be positive")
    external_temperature, external_moisture = boundary_at(t_next_s, environment, post_boundary)
    radius_m = _radius_m_at(t_next_s, radius, config.fixed_radius_cm)
    temperature_guess = previous_temperature.copy()
    moisture_guess = previous_moisture.copy()
    last_temperature_error = np.inf
    last_moisture_error = np.inf
    for iteration in range(1, config.maximum_picard_iterations + 1):
        rho_cp = density(moisture_guess) * heat_capacity(moisture_guess)
        next_temperature = _implicit_reference_step(
            previous_temperature,
            thermal_conductivity(moisture_guess),
            rho_cp,
            dt_s,
            radius_m,
            config.heat_transfer_w_m2_k,
            external_temperature,
            geometry,
            config.k_interface_mean,
        )
        next_moisture = _implicit_reference_step(
            previous_moisture,
            moisture_diffusivity(moisture_guess, next_temperature),
            np.ones_like(moisture_guess),
            dt_s,
            radius_m,
            config.mass_transfer_m_s,
            external_moisture,
            geometry,
            config.d_interface_mean,
        )
        last_temperature_error = float(np.max(np.abs(next_temperature - temperature_guess)))
        last_moisture_error = float(np.max(np.abs(next_moisture - moisture_guess)))
        if (
            last_temperature_error <= config.temperature_picard_tolerance
            and last_moisture_error <= config.moisture_picard_tolerance
        ):
            return next_temperature, next_moisture, iteration, last_temperature_error, last_moisture_error
        temperature_guess = next_temperature
        moisture_guess = next_moisture
    raise RuntimeError(
        "Picard iteration did not converge: "
        f"t={t_next_s:.6f}s, dt={dt_s:.6f}s, "
        f"temperature_error={last_temperature_error:.3e}, moisture_error={last_moisture_error:.3e}"
    )


def solve_problem4_be(
    environment: EnvironmentSeries,
    radius: RadiusSeries,
    config: BESolverConfig | None = None,
    post_boundary: PostBoundary | None = None,
) -> BEResult:
    config = config or BESolverConfig()
    post_boundary = post_boundary or post_boundary_from_tail(environment)
    geometry = build_reference_geometry(config.node_count)
    fixed_distance = np.asarray(config.fixed_distances_cm, dtype=float)
    temperature = np.full(config.node_count, config.initial_temperature_c, dtype=float)
    moisture = np.full(config.node_count, config.initial_moisture, dtype=float)
    time_s = 0.0
    output_times: list[float] = []
    output_radii: list[float] = []
    output_temperature: list[np.ndarray] = []
    output_moisture: list[np.ndarray] = []
    iteration_counts: list[int] = []
    temperature_errors: list[float] = []
    moisture_errors: list[float] = []
    minimum_raw_moisture = float(np.min(moisture))
    bisection_steps = 0
    event_time = None
    event_temperature = None
    event_moisture = None

    while time_s < config.fallback_time_limit_s - 1.0e-12:
        step_end = min(time_s + config.time_step_s, config.fallback_time_limit_s)
        if time_s < environment.terminal_time_s < step_end:
            step_end = environment.terminal_time_s
        next_sample = config.sample_interval_s * (np.floor(time_s / config.sample_interval_s) + 1.0)
        if time_s + 1.0e-10 < next_sample < step_end - 1.0e-10:
            step_end = float(next_sample)
        dt_s = step_end - time_s
        next_temperature, next_moisture, iterations, error_t, error_c = coupled_backward_euler_step(
            temperature,
            moisture,
            step_end,
            dt_s,
            geometry,
            environment,
            post_boundary,
            radius,
            config,
        )
        iteration_counts.append(iterations)
        temperature_errors.append(error_t)
        moisture_errors.append(error_c)
        minimum_raw_moisture = min(minimum_raw_moisture, float(np.min(next_moisture)))
        if minimum_raw_moisture < config.material_negative_tolerance:
            raise RuntimeError(f"materially negative moisture returned: {minimum_raw_moisture:.6g}")

        previous_event_value = float(np.max(moisture) - config.completion_threshold)
        next_event_value = float(np.max(next_moisture) - config.completion_threshold)
        if previous_event_value > 0.0 and next_event_value <= 0.0:
            left_time = time_s
            left_temperature = temperature.copy()
            left_moisture = moisture.copy()
            right_time = step_end
            right_temperature = next_temperature.copy()
            right_moisture = next_moisture.copy()
            while right_time - left_time > config.event_bracket_tolerance_s:
                middle_time = 0.5 * (left_time + right_time)
                middle_temperature, middle_moisture, _, _, _ = coupled_backward_euler_step(
                    left_temperature,
                    left_moisture,
                    middle_time,
                    middle_time - left_time,
                    geometry,
                    environment,
                    post_boundary,
                    radius,
                    config,
                )
                bisection_steps += 1
                if float(np.max(middle_moisture) - config.completion_threshold) <= 0.0:
                    right_time = middle_time
                    right_temperature = middle_temperature
                    right_moisture = middle_moisture
                else:
                    left_time = middle_time
                    left_temperature = middle_temperature
                    left_moisture = middle_moisture
            event_time = right_time
            event_temperature = right_temperature
            event_moisture = right_moisture
            break

        time_s = step_end
        temperature = next_temperature
        moisture = next_moisture
        if np.isclose(time_s % config.sample_interval_s, 0.0, atol=1.0e-8):
            radius_cm = 100.0 * _radius_m_at(time_s, radius, config.fixed_radius_cm)
            output_times.append(time_s)
            output_radii.append(radius_cm)
            output_temperature.append(sample_physical_profile(temperature, geometry, radius_cm, fixed_distance))
            output_moisture.append(sample_physical_profile(moisture, geometry, radius_cm, fixed_distance))

    if event_time is None or event_temperature is None or event_moisture is None:
        raise RuntimeError(
            f"drying threshold was not reached by {config.fallback_time_limit_s / 3600.0:.1f} h"
        )
    event_radius_cm = 100.0 * _radius_m_at(event_time, radius, config.fixed_radius_cm)
    diagnostics = BEDiagnostics(
        accepted_steps=len(iteration_counts),
        bisection_steps=bisection_steps,
        maximum_picard_iterations_used=int(max(iteration_counts)),
        mean_picard_iterations=float(np.mean(iteration_counts)),
        unconverged_steps=0,
        maximum_final_temperature_iteration_error=float(max(temperature_errors)),
        maximum_final_moisture_iteration_error=float(max(moisture_errors)),
        minimum_raw_moisture=minimum_raw_moisture,
    )
    return BEResult(
        time_s=np.asarray(output_times, dtype=float),
        radius_cm=np.asarray(output_radii, dtype=float),
        fixed_distance_cm=fixed_distance,
        temperature_c=np.vstack(output_temperature) if output_temperature else np.empty((0, len(fixed_distance) + 1)),
        moisture=np.vstack(output_moisture) if output_moisture else np.empty((0, len(fixed_distance) + 1)),
        drying_event_time_s=float(event_time),
        event_radius_cm=event_radius_cm,
        event_temperature_internal=event_temperature.copy(),
        event_moisture_internal=event_moisture.copy(),
        event_output_temperature=sample_physical_profile(
            event_temperature, geometry, event_radius_cm, fixed_distance
        ),
        event_output_moisture=sample_physical_profile(event_moisture, geometry, event_radius_cm, fixed_distance),
        diagnostics=diagnostics,
    )
