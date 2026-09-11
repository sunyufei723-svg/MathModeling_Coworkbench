from __future__ import annotations

from dataclasses import dataclass
from math import floor
from typing import Callable

import numpy as np
from scipy.integrate import solve_ivp

try:
    from .environment import EnvironmentSeries, PostBoundary, boundary_at, post_boundary_from_tail
    from .fvm import (
        ReferenceGeometry,
        build_coupled_jacobian_sparsity,
        build_reference_geometry,
        interface_values,
        internal_flux_numerator,
        sample_physical_profile,
    )
    from .model import density, heat_capacity, moisture_diffusivity, thermal_conductivity
    from .radius import RadiusSeries
except ImportError:
    from environment import EnvironmentSeries, PostBoundary, boundary_at, post_boundary_from_tail  # type: ignore
    from fvm import (  # type: ignore
        ReferenceGeometry,
        build_coupled_jacobian_sparsity,
        build_reference_geometry,
        interface_values,
        internal_flux_numerator,
        sample_physical_profile,
    )
    from model import density, heat_capacity, moisture_diffusivity, thermal_conductivity  # type: ignore
    from radius import RadiusSeries  # type: ignore


DEFAULT_FIXED_DISTANCES_CM = tuple(float(value) for value in np.round(np.arange(0.0, 2.0, 0.1), 10))


@dataclass(frozen=True)
class SolverConfig:
    node_count: int = 801
    sample_interval_s: int = 60
    report_interval_s: int = 60
    fixed_distances_cm: tuple[float, ...] = DEFAULT_FIXED_DISTANCES_CM
    initial_temperature_c: float = 28.0
    initial_moisture: float = 2.55
    completion_threshold: float = 0.15
    heat_transfer_w_m2_k: float = 25.0
    mass_transfer_m_s: float = 8.0e-7
    k_interface_mean: str = "harmonic"
    d_interface_mean: str = "harmonic"
    model_form: str = "material"
    fixed_radius_cm: float | None = None
    relative_tolerance: float = 1.0e-8
    temperature_absolute_tolerance: float = 1.0e-8
    moisture_absolute_tolerance: float = 1.0e-10
    max_time_step_s: float = 30.0
    initial_time_limit_s: float = 72.0 * 3600.0
    fallback_time_limit_s: float = 96.0 * 3600.0
    material_negative_tolerance: float = -1.0e-8
    monotonicity_tolerance: float = 1.0e-8


@dataclass(frozen=True)
class SolverDiagnostics:
    internal_node_count: int
    state_size: int
    function_evaluations: int
    jacobian_evaluations: int
    lu_decompositions: int
    phase1_end_time_s: float
    first_limit_reached_without_event: bool
    event_count: int
    event_direction: int
    minimum_temperature_c: float
    maximum_temperature_c: float
    minimum_raw_moisture: float
    clipped_cell_count: int
    maximum_clip_magnitude: float
    radial_monotonicity_all_outputs: bool
    non_center_argmax_count: int
    maximum_normalized_balance_residual: float
    dry_mass_index_relative_range: float


@dataclass(frozen=True)
class SimulationResult:
    time_s: np.ndarray
    radius_cm: np.ndarray
    fixed_distance_cm: np.ndarray
    temperature_c: np.ndarray
    moisture: np.ndarray
    argmax_xi: np.ndarray
    argmax_radius_cm: np.ndarray
    max_moisture: np.ndarray
    center_moisture: np.ndarray
    radial_monotonicity: np.ndarray
    dry_mass_index: np.ndarray
    drying_event_time_s: float
    report_end_time_s: int
    previous_report_time_s: int
    previous_report_max_moisture: float
    report_max_moisture: float
    event_radius_cm: float
    event_temperature_internal: np.ndarray
    event_moisture_internal: np.ndarray
    event_output_temperature: np.ndarray
    event_output_moisture: np.ndarray
    diagnostics: SolverDiagnostics


def drying_event_value(state: np.ndarray, node_count: int, threshold: float) -> float:
    return float(np.max(state[node_count:]) - threshold)


def _radius_values(t_s: float, radius: RadiusSeries, config: SolverConfig) -> tuple[float, float]:
    if config.fixed_radius_cm is not None:
        if config.fixed_radius_cm <= 0.0:
            raise ValueError("fixed_radius_cm must be positive")
        return config.fixed_radius_cm / 100.0, 0.0
    radius_cm = radius.radius_cm_at(t_s)
    radius_rate_cm_s = radius.radius_rate_cm_s_at(t_s)
    return radius_cm / 100.0, radius_rate_cm_s / max(radius_cm, 1.0e-30)


def build_coupled_rhs(
    geometry: ReferenceGeometry,
    environment: EnvironmentSeries,
    post_boundary: PostBoundary,
    radius: RadiusSeries,
    config: SolverConfig,
) -> Callable[[float, np.ndarray], np.ndarray]:
    if config.model_form not in {"material", "eulerian"}:
        raise ValueError("model_form must be 'material' or 'eulerian'")
    node_count = geometry.node_count

    def rhs(t_s: float, state: np.ndarray) -> np.ndarray:
        temperature = state[:node_count]
        moisture = state[node_count:]
        radius_m, radius_rate_ratio_s = _radius_values(t_s, radius, config)
        external_temperature, external_moisture = boundary_at(t_s, environment, post_boundary)

        node_k = thermal_conductivity(moisture)
        node_d = moisture_diffusivity(moisture, temperature)
        heat_numerator = internal_flux_numerator(
            temperature,
            interface_values(node_k, config.k_interface_mean),
            geometry,
        )
        moisture_numerator = internal_flux_numerator(
            moisture,
            interface_values(node_d, config.d_interface_mean),
            geometry,
        )
        heat_numerator[-1] += radius_m * config.heat_transfer_w_m2_k * (
            external_temperature - temperature[-1]
        )
        moisture_numerator[-1] += radius_m * config.mass_transfer_m_s * (
            external_moisture - moisture[-1]
        )

        rho_cp = density(moisture) * heat_capacity(moisture)
        temperature_rate = heat_numerator / (radius_m**2 * rho_cp * geometry.volumes_hat)
        moisture_rate = moisture_numerator / (radius_m**2 * geometry.volumes_hat)

        if config.model_form == "eulerian":
            temperature_gradient = np.gradient(temperature, geometry.dxi, edge_order=2)
            moisture_gradient = np.gradient(moisture, geometry.dxi, edge_order=2)
            temperature_rate += geometry.xi * radius_rate_ratio_s * temperature_gradient
            moisture_rate += geometry.xi * radius_rate_ratio_s * moisture_gradient

        derivative = np.concatenate([temperature_rate, moisture_rate])
        if not np.isfinite(derivative).all():
            raise RuntimeError("RHS returned non-finite values")
        return derivative

    return rhs


def _evaluate_segments(segments: list, times: np.ndarray) -> np.ndarray:
    states = np.empty((segments[0].y.shape[0], times.size), dtype=float)
    assigned = np.zeros(times.size, dtype=bool)
    for segment in segments:
        mask = (~assigned) & (times >= segment.t[0] - 1.0e-8) & (times <= segment.t[-1] + 1.0e-8)
        if np.any(mask):
            states[:, mask] = segment.sol(times[mask])
            assigned[mask] = True
    if not assigned.all():
        raise RuntimeError(f"no dense-output segment covers {times[~assigned]}")
    return states


def _sample_times(event_time_s: float, report_end_time_s: int, config: SolverConfig) -> np.ndarray:
    regular = np.arange(
        config.sample_interval_s,
        floor(event_time_s / config.sample_interval_s) * config.sample_interval_s + 1,
        config.sample_interval_s,
        dtype=float,
    )
    required = np.array(
        [float(report_end_time_s - config.report_interval_s), float(report_end_time_s)],
        dtype=float,
    )
    return np.unique(np.concatenate([regular, required]))


def _normalized_balance_residual(
    t_s: float,
    state: np.ndarray,
    rhs: Callable[[float, np.ndarray], np.ndarray],
    geometry: ReferenceGeometry,
    environment: EnvironmentSeries,
    post_boundary: PostBoundary,
    radius: RadiusSeries,
    config: SolverConfig,
) -> float:
    if config.model_form != "material":
        return 0.0
    n = geometry.node_count
    moisture = state[n:]
    radius_m, _ = _radius_values(t_s, radius, config)
    _, external_moisture = boundary_at(t_s, environment, post_boundary)
    boundary_term = config.mass_transfer_m_s * (external_moisture - moisture[-1]) / radius_m
    weighted_rate = float(np.sum(rhs(t_s, state)[n:] * geometry.volumes_hat))
    residual = weighted_rate - boundary_term
    scale = abs(weighted_rate) + abs(boundary_term) + 1.0e-30
    return abs(residual) / scale


def _dry_mass_index(radius_m: float, moisture: np.ndarray, geometry: ReferenceGeometry) -> float:
    return float(
        radius_m**2
        * np.sum(density(moisture) / (1.0 + np.asarray(moisture, dtype=float)) * geometry.volumes_hat)
    )


def solve_problem4_bdf(
    environment: EnvironmentSeries,
    radius: RadiusSeries,
    config: SolverConfig | None = None,
    post_boundary: PostBoundary | None = None,
) -> SimulationResult:
    """严格物质坐标 FVM + 联合状态自适应 BDF + 连续终止事件。"""

    config = config or SolverConfig()
    post_boundary = post_boundary or post_boundary_from_tail(environment)
    if environment.time_s[0] > 0.0:
        raise ValueError("environment must start at or before t=0")
    if config.initial_time_limit_s <= environment.terminal_time_s:
        raise ValueError("initial_time_limit_s must exceed attachment terminal time")
    if config.fallback_time_limit_s <= config.initial_time_limit_s:
        raise ValueError("fallback_time_limit_s must exceed initial_time_limit_s")
    if config.sample_interval_s <= 0 or config.report_interval_s <= 0:
        raise ValueError("output intervals must be positive")

    geometry = build_reference_geometry(config.node_count)
    node_count = geometry.node_count
    jacobian_pattern = build_coupled_jacobian_sparsity(node_count)
    rhs = build_coupled_rhs(geometry, environment, post_boundary, radius, config)
    initial_state = np.concatenate(
        [
            np.full(node_count, config.initial_temperature_c, dtype=float),
            np.full(node_count, config.initial_moisture, dtype=float),
        ]
    )
    atol = np.concatenate(
        [
            np.full(node_count, config.temperature_absolute_tolerance),
            np.full(node_count, config.moisture_absolute_tolerance),
        ]
    )

    def integrate(start: float, end: float, state: np.ndarray, with_event: bool):
        events = None
        if with_event:
            def event(_: float, y: np.ndarray) -> float:
                return drying_event_value(y, node_count, config.completion_threshold)

            event.terminal = True
            event.direction = -1
            events = event
        solution = solve_ivp(
            rhs,
            (float(start), float(end)),
            state,
            method="BDF",
            events=events,
            dense_output=True,
            rtol=config.relative_tolerance,
            atol=atol,
            max_step=config.max_time_step_s,
            jac_sparsity=jacobian_pattern,
        )
        if not solution.success:
            raise RuntimeError(f"BDF integration failed: {solution.message}")
        if not np.isfinite(solution.y).all():
            raise RuntimeError("BDF integration returned non-finite values")
        return solution

    segments = []
    phase1 = integrate(0.0, environment.terminal_time_s, initial_state, False)
    segments.append(phase1)
    if drying_event_value(phase1.y[:, -1], node_count, config.completion_threshold) <= 0.0:
        raise RuntimeError("drying threshold was reached before attachment boundary ended")

    phase2 = integrate(
        environment.terminal_time_s,
        config.initial_time_limit_s,
        phase1.y[:, -1],
        True,
    )
    segments.append(phase2)
    first_limit_reached = len(phase2.t_events[0]) == 0
    if first_limit_reached:
        phase3 = integrate(
            config.initial_time_limit_s,
            config.fallback_time_limit_s,
            phase2.y[:, -1],
            True,
        )
        segments.append(phase3)
        if len(phase3.t_events[0]) == 0:
            terminal_max = float(np.max(phase3.y[node_count:, -1]))
            raise RuntimeError(
                f"drying threshold was not reached by {config.fallback_time_limit_s / 3600.0:.1f} h; "
                f"max moisture={terminal_max:.9g}"
            )
        event_time = float(phase3.t_events[0][0])
        event_state = phase3.y_events[0][0]
    else:
        event_time = float(phase2.t_events[0][0])
        event_state = phase2.y_events[0][0]

    report_end = int(config.report_interval_s * (floor(event_time / config.report_interval_s) + 1))
    extension = integrate(event_time, float(report_end), event_state, False)
    while drying_event_value(extension.y[:, -1], node_count, config.completion_threshold) >= 0.0:
        report_end += config.report_interval_s
        extension = integrate(event_time, float(report_end), event_state, False)
    segments.append(extension)

    previous_report = report_end - config.report_interval_s
    sample_times = _sample_times(event_time, report_end, config)
    sample_states = _evaluate_segments(segments, sample_times)
    sample_temperature = sample_states[:node_count, :].T
    sample_moisture = sample_states[node_count:, :].T
    radius_cm = np.array(
        [100.0 * _radius_values(float(t_s), radius, config)[0] for t_s in sample_times],
        dtype=float,
    )
    fixed_distance = np.asarray(config.fixed_distances_cm, dtype=float)
    output_temperature = np.vstack(
        [
            sample_physical_profile(profile, geometry, r_cm, fixed_distance)
            for profile, r_cm in zip(sample_temperature, radius_cm, strict=True)
        ]
    )
    output_moisture = np.vstack(
        [
            sample_physical_profile(profile, geometry, r_cm, fixed_distance)
            for profile, r_cm in zip(sample_moisture, radius_cm, strict=True)
        ]
    )

    argmax_indices = np.argmax(sample_moisture, axis=1)
    argmax_xi = geometry.xi[argmax_indices]
    argmax_radius_cm = argmax_xi * radius_cm
    max_moisture = np.max(sample_moisture, axis=1)
    monotonicity = np.all(np.diff(sample_moisture, axis=1) <= config.monotonicity_tolerance, axis=1)
    balance_residuals = np.array(
        [
            _normalized_balance_residual(
                float(t_s), sample_states[:, index], rhs, geometry, environment, post_boundary, radius, config
            )
            for index, t_s in enumerate(sample_times)
        ],
        dtype=float,
    )
    dry_mass = np.array(
        [
            _dry_mass_index(r_cm / 100.0, profile, geometry)
            for r_cm, profile in zip(radius_cm, sample_moisture, strict=True)
        ],
        dtype=float,
    )
    initial_radius_m, _ = _radius_values(0.0, radius, config)
    initial_dry_mass = _dry_mass_index(initial_radius_m, initial_state[node_count:], geometry)
    dry_mass_with_initial = np.concatenate([[initial_dry_mass], dry_mass])
    dry_mass_relative_range = float(
        (np.max(dry_mass_with_initial) - np.min(dry_mass_with_initial))
        / max(abs(initial_dry_mass), 1.0e-30)
    )

    event_radius_cm = 100.0 * _radius_values(event_time, radius, config)[0]
    event_temperature = event_state[:node_count].copy()
    event_moisture = event_state[node_count:].copy()
    event_output_temperature = sample_physical_profile(
        event_temperature, geometry, event_radius_cm, fixed_distance
    )
    event_output_moisture = sample_physical_profile(
        event_moisture, geometry, event_radius_cm, fixed_distance
    )
    previous_state = _evaluate_segments(segments, np.array([float(previous_report)]))[:, 0]
    report_state = extension.sol(float(report_end))
    minimum_raw_moisture = float(
        min(np.min(sample_moisture), np.min(event_moisture), np.min(report_state[node_count:]))
    )
    if minimum_raw_moisture < config.material_negative_tolerance:
        raise RuntimeError(f"materially negative moisture returned: {minimum_raw_moisture:.6g}")

    diagnostics = SolverDiagnostics(
        internal_node_count=node_count,
        state_size=2 * node_count,
        function_evaluations=int(sum(segment.nfev for segment in segments)),
        jacobian_evaluations=int(sum(segment.njev for segment in segments)),
        lu_decompositions=int(sum(segment.nlu for segment in segments)),
        phase1_end_time_s=environment.terminal_time_s,
        first_limit_reached_without_event=first_limit_reached,
        event_count=1,
        event_direction=-1,
        minimum_temperature_c=float(
            min(config.initial_temperature_c, np.min(sample_temperature), np.min(event_temperature))
        ),
        maximum_temperature_c=float(max(np.max(sample_temperature), np.max(event_temperature))),
        minimum_raw_moisture=minimum_raw_moisture,
        clipped_cell_count=0,
        maximum_clip_magnitude=0.0,
        radial_monotonicity_all_outputs=bool(monotonicity.all()),
        non_center_argmax_count=int(np.count_nonzero(argmax_indices)),
        maximum_normalized_balance_residual=float(np.max(balance_residuals)),
        dry_mass_index_relative_range=dry_mass_relative_range,
    )
    return SimulationResult(
        time_s=sample_times,
        radius_cm=radius_cm,
        fixed_distance_cm=fixed_distance,
        temperature_c=output_temperature,
        moisture=output_moisture,
        argmax_xi=argmax_xi,
        argmax_radius_cm=argmax_radius_cm,
        max_moisture=max_moisture,
        center_moisture=sample_moisture[:, 0],
        radial_monotonicity=monotonicity,
        dry_mass_index=dry_mass,
        drying_event_time_s=event_time,
        report_end_time_s=report_end,
        previous_report_time_s=previous_report,
        previous_report_max_moisture=float(np.max(previous_state[node_count:])),
        report_max_moisture=float(np.max(report_state[node_count:])),
        event_radius_cm=event_radius_cm,
        event_temperature_internal=event_temperature,
        event_moisture_internal=event_moisture,
        event_output_temperature=event_output_temperature,
        event_output_moisture=event_output_moisture,
        diagnostics=diagnostics,
    )
