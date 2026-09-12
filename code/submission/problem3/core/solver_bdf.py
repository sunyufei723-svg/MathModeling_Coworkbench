from __future__ import annotations

from dataclasses import dataclass
from math import ceil
from typing import Callable

import numpy as np
from scipy.integrate import solve_ivp

try:
    from .fvm import (
        RadialGeometry,
        build_coupled_jacobian_sparsity,
        build_radial_geometry,
        interface_values,
        internal_flux_numerator,
        sample_profiles,
    )
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
    from fvm import (  # type: ignore
        RadialGeometry,
        build_coupled_jacobian_sparsity,
        build_radial_geometry,
        interface_values,
        internal_flux_numerator,
        sample_profiles,
    )
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
class SolverConfig:
    radius_cm: float = 2.0
    internal_dr_cm: float = 0.025
    output_dr_cm: float = 0.1
    output_interval_s: int = 60
    initial_temperature_c: float = 28.0
    initial_moisture: float = 2.55
    completion_threshold: float = 0.15
    heat_transfer_w_m2_k: float = 25.0
    mass_transfer_m_s: float = 8e-7
    interface_mean: str = "harmonic"
    relative_tolerance: float = 1e-8
    temperature_absolute_tolerance: float = 1e-8
    moisture_absolute_tolerance: float = 1e-10
    max_time_step_s: float = 60.0
    initial_time_limit_s: float = 72.0 * 3600.0
    fallback_time_limit_s: float = 96.0 * 3600.0
    extended_time_limit_s: float | None = None
    material_negative_tolerance: float = -1e-8
    monotonicity_tolerance: float = 1e-8


@dataclass(frozen=True)
class SolverDiagnostics:
    internal_node_count: int
    state_size: int
    function_evaluations: int
    jacobian_evaluations: int
    lu_decompositions: int
    phase1_end_time_s: float
    first_limit_reached_without_event: bool
    fallback_limit_reached_without_event: bool
    event_count: int
    event_direction: int
    minimum_temperature_c: float
    maximum_temperature_c: float
    minimum_raw_moisture: float
    clipped_cell_count: int
    maximum_clip_magnitude: float
    radial_monotonicity_all_outputs: bool
    non_center_argmax_count: int
    maximum_normalized_mass_balance_residual: float


@dataclass(frozen=True)
class SimulationResult:
    time_s: np.ndarray
    radius_cm: np.ndarray
    temperature_c: np.ndarray
    moisture: np.ndarray
    argmax_radius_cm: np.ndarray
    max_moisture: np.ndarray
    center_moisture: np.ndarray
    radial_monotonicity: np.ndarray
    drying_event_time_s: float
    report_end_time_s: int
    event_temperature_c: np.ndarray
    event_moisture: np.ndarray
    event_internal_radius_cm: np.ndarray
    event_internal_moisture: np.ndarray
    diagnostics: SolverDiagnostics


def drying_event_value(state: np.ndarray, node_count: int, threshold: float) -> float:
    return float(np.max(state[node_count:]) - threshold)


def _boundary_values(
    t_s: float,
    environment: EnvironmentSeries,
    post_boundary: PostBoundary,
) -> tuple[float, float]:
    if t_s <= environment.terminal_time_s:
        return environment.interpolated_temperature(t_s), environment.interpolated_moisture(t_s)
    return post_boundary.temperature_c, post_boundary.moisture


def build_coupled_rhs(
    geometry: RadialGeometry,
    environment: EnvironmentSeries,
    post_boundary: PostBoundary,
    config: SolverConfig,
) -> Callable[[float, np.ndarray], np.ndarray]:
    node_count = geometry.node_count

    def rhs(t_s: float, state: np.ndarray) -> np.ndarray:
        temperature = state[:node_count]
        moisture = state[node_count:]
        node_k = thermal_conductivity(moisture)
        node_d = moisture_diffusivity(moisture, temperature)
        face_k = interface_values(node_k, config.interface_mean)
        face_d = interface_values(node_d, config.interface_mean)
        heat_numerator = internal_flux_numerator(temperature, face_k, geometry)
        moisture_numerator = internal_flux_numerator(moisture, face_d, geometry)
        external_temperature, external_moisture = _boundary_values(t_s, environment, post_boundary)
        heat_numerator[-1] += (
            config.heat_transfer_w_m2_k
            * geometry.surface_area_m2_per_m
            * (external_temperature - temperature[-1])
        )
        moisture_numerator[-1] += (
            config.mass_transfer_m_s
            * geometry.surface_area_m2_per_m
            * (external_moisture - moisture[-1])
        )
        rho_cp = density(moisture) * heat_capacity(moisture)
        temperature_rate = heat_numerator / (rho_cp * geometry.volumes_m3_per_m)
        moisture_rate = moisture_numerator / geometry.volumes_m3_per_m
        return np.concatenate([temperature_rate, moisture_rate])

    return rhs


def _evaluate_segments(segments: list, times: np.ndarray) -> np.ndarray:
    if times.size == 0:
        raise ValueError("times must not be empty")
    state_count = int(segments[0].y.shape[0])
    evaluated = np.empty((state_count, times.size), dtype=float)
    assigned = np.zeros(times.size, dtype=bool)
    for segment in segments:
        mask = (~assigned) & (times >= segment.t[0] - 1e-8) & (times <= segment.t[-1] + 1e-8)
        if np.any(mask):
            evaluated[:, mask] = segment.sol(times[mask])
            assigned[mask] = True
    if not assigned.all():
        raise RuntimeError(f"no dense-output segment covers {times[~assigned]}")
    return evaluated


def _normalized_mass_balance_residual(
    t_s: float,
    state: np.ndarray,
    rhs: Callable[[float, np.ndarray], np.ndarray],
    geometry: RadialGeometry,
    environment: EnvironmentSeries,
    post_boundary: PostBoundary,
    config: SolverConfig,
) -> float:
    n = geometry.node_count
    moisture = state[n:]
    rate = rhs(t_s, state)[n:]
    _, external_moisture = _boundary_values(t_s, environment, post_boundary)
    surface_flux = (
        config.mass_transfer_m_s
        * geometry.surface_area_m2_per_m
        * (external_moisture - moisture[-1])
    )
    residual = float(np.sum(rate * geometry.volumes_m3_per_m) - surface_flux)
    scale = float(np.sum(np.abs(rate * geometry.volumes_m3_per_m)) + abs(surface_flux) + 1e-30)
    return abs(residual) / scale


def solve_problem3_bdf(
    environment: EnvironmentSeries,
    config: SolverConfig | None = None,
    post_boundary: PostBoundary | None = None,
) -> SimulationResult:
    """两阶段积分耦合状态 [T_0..T_N,C_0..C_N]，以全域最大水分触发终止事件。"""

    config = config or SolverConfig()
    post_boundary = post_boundary or post_boundary_from_tail(environment)
    if environment.time_s[0] > 0.0:
        raise ValueError("environment must start at or before t=0")
    if config.initial_time_limit_s <= environment.terminal_time_s:
        raise ValueError("initial_time_limit_s must exceed the attachment terminal time")
    if config.fallback_time_limit_s <= config.initial_time_limit_s:
        raise ValueError("fallback_time_limit_s must exceed initial_time_limit_s")
    if config.extended_time_limit_s is not None and config.extended_time_limit_s <= config.fallback_time_limit_s:
        raise ValueError("extended_time_limit_s must exceed fallback_time_limit_s")
    if config.output_interval_s <= 0:
        raise ValueError("output_interval_s must be positive")

    geometry = build_radial_geometry(config.radius_cm, config.internal_dr_cm)
    internal_radius_cm = geometry.radius_m * 100.0
    output_geometry = build_radial_geometry(config.radius_cm, config.output_dr_cm)
    output_radius_cm = output_geometry.radius_m * 100.0
    node_count = geometry.node_count
    jacobian_pattern = build_coupled_jacobian_sparsity(node_count)
    rhs = build_coupled_rhs(geometry, environment, post_boundary, config)
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
            def event(t_s: float, y: np.ndarray) -> float:
                del t_s
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
    phase1_state = phase1.y[:, -1]
    if drying_event_value(phase1_state, node_count, config.completion_threshold) <= 0.0:
        raise RuntimeError("drying threshold was reached before the attachment boundary ended")

    phase2 = integrate(environment.terminal_time_s, config.initial_time_limit_s, phase1_state, True)
    segments.append(phase2)
    first_limit_reached = len(phase2.t_events[0]) == 0
    fallback_limit_reached = False
    event_time = None
    event_state = None
    if not first_limit_reached:
        event_time = float(phase2.t_events[0][0])
        event_state = phase2.y_events[0][0]
    else:
        phase3 = integrate(config.initial_time_limit_s, config.fallback_time_limit_s, phase2.y[:, -1], True)
        segments.append(phase3)
        if len(phase3.t_events[0]) == 0:
            fallback_limit_reached = True
            if config.extended_time_limit_s is None:
                terminal_max = float(np.max(phase3.y[node_count:, -1]))
                terminal_argmax = int(np.argmax(phase3.y[node_count:, -1]))
                raise RuntimeError(
                    f"drying threshold was not reached by {config.fallback_time_limit_s / 3600.0:.1f} h; "
                    f"max moisture={terminal_max:.9g} at r={internal_radius_cm[terminal_argmax]:.9g} cm"
                )
            phase4 = integrate(
                config.fallback_time_limit_s,
                config.extended_time_limit_s,
                phase3.y[:, -1],
                True,
            )
            segments.append(phase4)
            if len(phase4.t_events[0]) == 0:
                terminal_max = float(np.max(phase4.y[node_count:, -1]))
                terminal_argmax = int(np.argmax(phase4.y[node_count:, -1]))
                raise RuntimeError(
                    f"drying threshold was not reached by {config.extended_time_limit_s / 3600.0:.1f} h; "
                    f"max moisture={terminal_max:.9g} at r={internal_radius_cm[terminal_argmax]:.9g} cm"
                )
            event_time = float(phase4.t_events[0][0])
            event_state = phase4.y_events[0][0]
        else:
            event_time = float(phase3.t_events[0][0])
            event_state = phase3.y_events[0][0]

    assert event_time is not None and event_state is not None
    report_end = int(config.output_interval_s * ceil(event_time / config.output_interval_s))
    if report_end <= event_time + 1e-9:
        report_end += config.output_interval_s
    extension = integrate(event_time, float(report_end), event_state, False)
    while drying_event_value(extension.y[:, -1], node_count, config.completion_threshold) >= 0.0:
        report_end += config.output_interval_s
        extension = integrate(event_time, float(report_end), event_state, False)
    segments.append(extension)

    output_times = np.arange(config.output_interval_s, report_end + 1, config.output_interval_s, dtype=float)
    internal_states = _evaluate_segments(segments, output_times)
    internal_temperature = internal_states[:node_count, :].T
    internal_moisture = internal_states[node_count:, :].T
    minimum_raw_moisture = float(min(np.min(internal_moisture), np.min(event_state[node_count:])))
    if minimum_raw_moisture < config.material_negative_tolerance:
        raise RuntimeError(f"materially negative moisture returned: {minimum_raw_moisture:.6g}")

    output_temperature = sample_profiles(internal_radius_cm, output_radius_cm, internal_temperature)
    output_moisture = sample_profiles(internal_radius_cm, output_radius_cm, internal_moisture)
    event_temperature = sample_profiles(
        internal_radius_cm,
        output_radius_cm,
        event_state[:node_count][None, :],
    )[0]
    event_moisture = sample_profiles(
        internal_radius_cm,
        output_radius_cm,
        event_state[node_count:][None, :],
    )[0]
    argmax_indices = np.argmax(internal_moisture, axis=1)
    argmax_radius = internal_radius_cm[argmax_indices]
    max_moisture = np.max(internal_moisture, axis=1)
    monotonicity = np.all(np.diff(internal_moisture, axis=1) <= config.monotonicity_tolerance, axis=1)
    mass_residuals = np.array(
        [
            _normalized_mass_balance_residual(
                float(t_s), internal_states[:, index], rhs, geometry, environment, post_boundary, config
            )
            for index, t_s in enumerate(output_times)
        ]
    )
    all_solutions = segments
    diagnostics = SolverDiagnostics(
        internal_node_count=node_count,
        state_size=2 * node_count,
        function_evaluations=int(sum(solution.nfev for solution in all_solutions)),
        jacobian_evaluations=int(sum(solution.njev for solution in all_solutions)),
        lu_decompositions=int(sum(solution.nlu for solution in all_solutions)),
        phase1_end_time_s=environment.terminal_time_s,
        first_limit_reached_without_event=first_limit_reached,
        fallback_limit_reached_without_event=fallback_limit_reached,
        event_count=1,
        event_direction=-1,
        minimum_temperature_c=float(min(np.min(internal_temperature), np.min(event_state[:node_count]))),
        maximum_temperature_c=float(max(np.max(internal_temperature), np.max(event_state[:node_count]))),
        minimum_raw_moisture=minimum_raw_moisture,
        clipped_cell_count=0,
        maximum_clip_magnitude=0.0,
        radial_monotonicity_all_outputs=bool(monotonicity.all()),
        non_center_argmax_count=int(np.count_nonzero(argmax_indices)),
        maximum_normalized_mass_balance_residual=float(np.max(mass_residuals)),
    )
    return SimulationResult(
        time_s=output_times,
        radius_cm=output_radius_cm,
        temperature_c=output_temperature,
        moisture=output_moisture,
        argmax_radius_cm=argmax_radius,
        max_moisture=max_moisture,
        center_moisture=internal_moisture[:, 0],
        radial_monotonicity=monotonicity,
        drying_event_time_s=event_time,
        report_end_time_s=report_end,
        event_temperature_c=event_temperature,
        event_moisture=event_moisture,
        event_internal_radius_cm=internal_radius_cm,
        event_internal_moisture=event_state[node_count:].copy(),
        diagnostics=diagnostics,
    )
