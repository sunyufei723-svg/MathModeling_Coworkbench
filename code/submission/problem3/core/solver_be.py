from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from scipy.linalg.lapack import dgtsv

try:
    from .fvm import RadialGeometry, build_radial_geometry, interface_values, sample_profiles
    from .model import (
        EnvironmentSeries,
        PostBoundary,
        density,
        heat_capacity,
        moisture_diffusivity,
        post_boundary_from_tail,
        thermal_conductivity,
    )
except ImportError:  # 允许直接运行本目录脚本
    from fvm import RadialGeometry, build_radial_geometry, interface_values, sample_profiles  # type: ignore
    from model import (  # type: ignore
        EnvironmentSeries,
        PostBoundary,
        density,
        heat_capacity,
        moisture_diffusivity,
        post_boundary_from_tail,
        thermal_conductivity,
    )


@dataclass(frozen=True)
class BESolverConfig:
    radius_cm: float = 2.0
    internal_dr_cm: float = 0.025
    output_dr_cm: float = 0.1
    time_step_s: float = 10.0
    output_interval_s: int = 60
    initial_temperature_c: float = 28.0
    initial_moisture: float = 2.55
    completion_threshold: float = 0.15
    heat_transfer_w_m2_k: float = 25.0
    mass_transfer_m_s: float = 8e-7
    interface_mean: str = "harmonic"
    maximum_picard_iterations: int = 20
    temperature_picard_tolerance: float = 1e-8
    moisture_picard_tolerance: float = 1e-10
    initial_time_limit_s: float = 72.0 * 3600.0
    fallback_time_limit_s: float = 96.0 * 3600.0
    event_bracket_tolerance_s: float = 0.5
    material_negative_tolerance: float = -1e-8


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
    temperature_c: np.ndarray
    moisture: np.ndarray
    drying_event_time_s: float
    event_temperature_c: np.ndarray
    event_moisture: np.ndarray
    event_internal_radius_cm: np.ndarray
    event_internal_moisture: np.ndarray
    diagnostics: BEDiagnostics


def _solve_tridiagonal(
    lower: np.ndarray,
    diagonal: np.ndarray,
    upper: np.ndarray,
    right_hand_side: np.ndarray,
) -> np.ndarray:
    n = diagonal.size
    if n < 2:
        raise ValueError("tridiagonal system must have at least two rows")
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


def _implicit_fvm_step(
    previous: np.ndarray,
    node_transport: np.ndarray,
    capacity: np.ndarray,
    dt_s: float,
    boundary_transfer: float,
    boundary_external: float,
    geometry: RadialGeometry,
    interface_mean: str,
) -> np.ndarray:
    face_transport = interface_values(node_transport, interface_mean)
    conductance = face_transport * geometry.interface_areas_m2_per_m / geometry.dr_m
    accumulation = capacity * geometry.volumes_m3_per_m / dt_s
    lower = -conductance.copy()
    upper = -conductance.copy()
    diagonal = accumulation.copy()
    diagonal[:-1] += conductance
    diagonal[1:] += conductance
    right_hand_side = accumulation * previous
    boundary_conductance = boundary_transfer * geometry.surface_area_m2_per_m
    diagonal[-1] += boundary_conductance
    right_hand_side[-1] += boundary_conductance * boundary_external
    return _solve_tridiagonal(lower, diagonal, upper, right_hand_side)


def _boundary_at(t_s: float, environment: EnvironmentSeries, post_boundary: PostBoundary) -> tuple[float, float]:
    if t_s <= environment.terminal_time_s:
        return environment.interpolated_temperature(t_s), environment.interpolated_moisture(t_s)
    return post_boundary.temperature_c, post_boundary.moisture


def coupled_backward_euler_step(
    previous_temperature: np.ndarray,
    previous_moisture: np.ndarray,
    t_next_s: float,
    dt_s: float,
    geometry: RadialGeometry,
    environment: EnvironmentSeries,
    post_boundary: PostBoundary,
    config: BESolverConfig,
) -> tuple[np.ndarray, np.ndarray, int, float, float]:
    if dt_s <= 0.0:
        raise ValueError("dt_s must be positive")
    external_temperature, external_moisture = _boundary_at(t_next_s, environment, post_boundary)
    temperature_guess = previous_temperature.copy()
    moisture_guess = previous_moisture.copy()
    last_temperature_error = np.inf
    last_moisture_error = np.inf
    for iteration in range(1, config.maximum_picard_iterations + 1):
        rho_cp = density(moisture_guess) * heat_capacity(moisture_guess)
        next_temperature = _implicit_fvm_step(
            previous_temperature,
            thermal_conductivity(moisture_guess),
            rho_cp,
            dt_s,
            config.heat_transfer_w_m2_k,
            external_temperature,
            geometry,
            config.interface_mean,
        )
        next_moisture = _implicit_fvm_step(
            previous_moisture,
            moisture_diffusivity(moisture_guess, next_temperature),
            np.ones_like(moisture_guess),
            dt_s,
            config.mass_transfer_m_s,
            external_moisture,
            geometry,
            config.interface_mean,
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


def solve_problem3_be(
    environment: EnvironmentSeries,
    config: BESolverConfig | None = None,
    post_boundary: PostBoundary | None = None,
) -> BEResult:
    config = config or BESolverConfig()
    post_boundary = post_boundary or post_boundary_from_tail(environment)
    if environment.time_s[0] > 0.0:
        raise ValueError("environment must start at or before t=0")
    geometry = build_radial_geometry(config.radius_cm, config.internal_dr_cm)
    internal_radius_cm = geometry.radius_m * 100.0
    output_radius_cm = build_radial_geometry(config.radius_cm, config.output_dr_cm).radius_m * 100.0
    temperature = np.full(geometry.node_count, config.initial_temperature_c, dtype=float)
    moisture = np.full(geometry.node_count, config.initial_moisture, dtype=float)
    time_s = 0.0
    output_times: list[float] = []
    output_temperature: list[np.ndarray] = []
    output_moisture: list[np.ndarray] = []
    iteration_counts: list[int] = []
    final_temperature_errors: list[float] = []
    final_moisture_errors: list[float] = []
    minimum_raw_moisture = float(np.min(moisture))
    bisection_steps = 0
    event_time = None
    event_temperature = None
    event_moisture = None

    while time_s < config.fallback_time_limit_s - 1e-12:
        step_end = min(time_s + config.time_step_s, config.fallback_time_limit_s)
        if time_s < environment.terminal_time_s < step_end:
            step_end = environment.terminal_time_s
        next_output = config.output_interval_s * (np.floor(time_s / config.output_interval_s) + 1.0)
        if time_s + 1e-10 < next_output < step_end - 1e-10:
            step_end = float(next_output)
        dt_s = step_end - time_s
        next_temperature, next_moisture, iterations, error_t, error_c = coupled_backward_euler_step(
            temperature,
            moisture,
            step_end,
            dt_s,
            geometry,
            environment,
            post_boundary,
            config,
        )
        iteration_counts.append(iterations)
        final_temperature_errors.append(error_t)
        final_moisture_errors.append(error_c)
        minimum_raw_moisture = min(minimum_raw_moisture, float(np.min(next_moisture)))
        if minimum_raw_moisture < config.material_negative_tolerance:
            raise RuntimeError(f"materially negative moisture returned: {minimum_raw_moisture:.6g}")

        previous_event_value = float(np.max(moisture) - config.completion_threshold)
        next_event_value = float(np.max(next_moisture) - config.completion_threshold)
        if previous_event_value > 0.0 and next_event_value <= 0.0:
            left_time = time_s
            left_temperature = temperature
            left_moisture = moisture
            right_time = step_end
            right_temperature = next_temperature
            right_moisture = next_moisture
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
        if np.isclose(time_s % config.output_interval_s, 0.0, atol=1e-8):
            output_times.append(time_s)
            output_temperature.append(temperature.copy())
            output_moisture.append(moisture.copy())

    if event_time is None or event_temperature is None or event_moisture is None:
        raise RuntimeError(
            f"drying threshold was not reached by {config.fallback_time_limit_s / 3600.0:.1f} h"
        )
    if not output_times:
        raise RuntimeError("no regular output was produced")

    output_temperature_internal = np.vstack(output_temperature)
    output_moisture_internal = np.vstack(output_moisture)
    diagnostics = BEDiagnostics(
        accepted_steps=len(iteration_counts),
        bisection_steps=bisection_steps,
        maximum_picard_iterations_used=int(max(iteration_counts)),
        mean_picard_iterations=float(np.mean(iteration_counts)),
        unconverged_steps=0,
        maximum_final_temperature_iteration_error=float(max(final_temperature_errors)),
        maximum_final_moisture_iteration_error=float(max(final_moisture_errors)),
        minimum_raw_moisture=minimum_raw_moisture,
    )
    return BEResult(
        time_s=np.asarray(output_times),
        radius_cm=output_radius_cm,
        temperature_c=sample_profiles(internal_radius_cm, output_radius_cm, output_temperature_internal),
        moisture=sample_profiles(internal_radius_cm, output_radius_cm, output_moisture_internal),
        drying_event_time_s=float(event_time),
        event_temperature_c=sample_profiles(
            internal_radius_cm, output_radius_cm, event_temperature[None, :]
        )[0],
        event_moisture=sample_profiles(
            internal_radius_cm, output_radius_cm, event_moisture[None, :]
        )[0],
        event_internal_radius_cm=internal_radius_cm,
        event_internal_moisture=event_moisture.copy(),
        diagnostics=diagnostics,
    )
