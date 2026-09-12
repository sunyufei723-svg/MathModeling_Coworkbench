from __future__ import annotations

import hashlib
import json
import sys
import time
from concurrent.futures import FIRST_COMPLETED, ProcessPoolExecutor, wait
from dataclasses import asdict, replace
from pathlib import Path
from typing import Iterable

import numpy as np
import pandas as pd

try:
    from .cache import JsonEvaluationCache
    from .parameters import PARAMETER_SPECS, point_from_unit
except ImportError:
    from cache import JsonEvaluationCache  # type: ignore
    from parameters import PARAMETER_SPECS, point_from_unit  # type: ignore


PROJECT_ROOT = Path(__file__).resolve().parents[4]
PROBLEM4_DIR = PROJECT_ROOT / "code" / "submission" / "problem4" / "core"
if str(PROBLEM4_DIR) not in sys.path:
    sys.path.insert(0, str(PROBLEM4_DIR))

from environment import EnvironmentSeries, PostBoundary  # noqa: E402
from model import PhysicalParameters  # noqa: E402
from radius import RadiusSeries  # noqa: E402
from solver_bdf import SolverConfig, solve_problem4_bdf  # noqa: E402


BASELINE_EVENT_TIME_S = 182968.2251620822


def load_inputs(attachment1: Path, attachment2: Path) -> tuple[EnvironmentSeries, RadiusSeries]:
    environment_frame = pd.read_excel(attachment1)
    radius_frame = pd.read_excel(attachment2)
    return (
        EnvironmentSeries(
            environment_frame.iloc[:, 0].to_numpy(dtype=float),
            environment_frame.iloc[:, 1].to_numpy(dtype=float),
            environment_frame.iloc[:, 2].to_numpy(dtype=float),
        ),
        RadiusSeries(
            radius_frame.iloc[:, 0].to_numpy(dtype=float),
            radius_frame.iloc[:, 1].to_numpy(dtype=float),
            "linear",
        ),
    )


def input_fingerprint(attachment1: Path, attachment2: Path) -> str:
    digest = hashlib.sha256()
    for path in (attachment1, attachment2):
        digest.update(path.read_bytes())
    return digest.hexdigest()


def evaluation_key(
    unit_point: np.ndarray,
    node_count: int,
    integration_method: str,
    fingerprint: str,
    include_profiles: bool = False,
) -> str:
    payload = {
        "unit_point": [round(float(value), 12) for value in unit_point],
        "node_count": int(node_count),
        "integration_method": integration_method,
        "input_fingerprint": fingerprint,
        "rtol": 1.0e-8,
        "temperature_atol": 1.0e-8,
        "moisture_atol": 1.0e-10,
        "max_step_s": 30.0,
        "initial_time_limit_s": 72.0 * 3600.0,
        "fallback_time_limit_s": 168.0 * 3600.0,
    }
    if include_profiles:
        payload["include_profiles"] = True
    return hashlib.sha256(json.dumps(payload, sort_keys=True).encode("utf-8")).hexdigest()


def _run_payload(payload: dict[str, object]) -> dict[str, object]:
    attachment1 = Path(str(payload["attachment1"]))
    attachment2 = Path(str(payload["attachment2"]))
    unit_point = np.asarray(payload["unit_point"], dtype=float)
    node_count = int(payload["node_count"])
    integration_method = str(payload["integration_method"])
    include_profiles = bool(payload.get("include_profiles", False))
    point = point_from_unit(unit_point)
    environment, radius = load_inputs(attachment1, attachment2)
    defaults = SolverConfig()
    physical = PhysicalParameters(
        density_intercept=760.0 * point["density_intercept_factor"],
        density_moisture_coefficient=90.0 * point["density_slope_factor"],
        diffusivity_prefactor=4.2e-4 * point["diffusivity_prefactor_factor"],
        diffusivity_moisture_parameter=0.30,
        activation_temperature_k=3850.0 * point["activation_temperature_factor"],
        shrinkage_amplitude_factor=point["shrinkage_amplitude_factor"],
    )
    config = replace(
        defaults,
        node_count=node_count,
        sample_interval_s=21600,
        report_interval_s=60,
        heat_transfer_w_m2_k=defaults.heat_transfer_w_m2_k * point["heat_transfer_factor"],
        mass_transfer_m_s=defaults.mass_transfer_m_s * point["mass_transfer_factor"],
        physical_parameters=physical,
        integration_method=integration_method,
        relative_tolerance=1.0e-8,
        temperature_absolute_tolerance=1.0e-8,
        moisture_absolute_tolerance=1.0e-10,
        max_time_step_s=30.0,
        initial_time_limit_s=72.0 * 3600.0,
        fallback_time_limit_s=168.0 * 3600.0,
    )
    post_boundary = PostBoundary(
        environment.terminal_temperature_c + point["ambient_temperature_delta_c"],
        environment.terminal_moisture * point["ambient_moisture_factor"],
    )
    started = time.perf_counter()
    result = solve_problem4_bdf(environment, radius, config, post_boundary)
    runtime_s = time.perf_counter() - started
    quality = bool(
        result.diagnostics.maximum_normalized_balance_residual < 1.0e-6
        and result.diagnostics.minimum_raw_moisture >= -1.0e-8
        and result.diagnostics.radial_monotonicity_all_outputs
        and int(np.argmax(result.event_moisture_internal)) == 0
        and result.report_max_moisture < config.completion_threshold
    )
    if not quality:
        raise RuntimeError("sensitivity run failed numerical quality checks")
    record = {
        "unit_point": [float(value) for value in unit_point],
        "parameters": point,
        "node_count": node_count,
        "integration_method": integration_method,
        "continuous_event_time_s": float(result.drying_event_time_s),
        "continuous_event_time_h": float(result.drying_event_time_s / 3600.0),
        "report_event_time_s": int(result.report_end_time_s),
        "report_event_time_h": float(result.report_end_time_s / 3600.0),
        "event_center_moisture": float(result.event_moisture_internal[0]),
        "event_surface_moisture": float(result.event_moisture_internal[-1]),
        "event_radius_cm": float(result.event_radius_cm),
        "event_argmax_index": int(np.argmax(result.event_moisture_internal)),
        "minimum_raw_moisture": float(result.diagnostics.minimum_raw_moisture),
        "maximum_normalized_balance_residual": float(
            result.diagnostics.maximum_normalized_balance_residual
        ),
        "radial_monotonicity": bool(result.diagnostics.radial_monotonicity_all_outputs),
        "function_evaluations": int(result.diagnostics.function_evaluations),
        "jacobian_evaluations": int(result.diagnostics.jacobian_evaluations),
        "lu_decompositions": int(result.diagnostics.lu_decompositions),
        "runtime_s": float(runtime_s),
        "quality_checks_passed": quality,
    }
    if include_profiles:
        record["sample_time_s"] = [float(value) for value in result.time_s]
        record["sample_moisture"] = [
            [None if not np.isfinite(value) else float(value) for value in row]
            for row in result.moisture
        ]
    return record


class ModelEvaluator:
    def __init__(
        self,
        attachment1: Path,
        attachment2: Path,
        cache_path: Path,
        workers: int = 1,
    ) -> None:
        self.attachment1 = Path(attachment1).resolve()
        self.attachment2 = Path(attachment2).resolve()
        self.cache = JsonEvaluationCache(Path(cache_path))
        self.workers = max(1, int(workers))
        self.fingerprint = input_fingerprint(self.attachment1, self.attachment2)

    def evaluate_many(
        self,
        unit_points: Iterable[np.ndarray | list[float]],
        node_count: int,
        integration_method: str = "BDF",
        include_profiles: bool = False,
    ) -> list[dict[str, object]]:
        points = [np.asarray(item, dtype=float) for item in unit_points]
        if any(point.shape != (len(PARAMETER_SPECS),) for point in points):
            raise ValueError("all unit points must contain every declared parameter")
        keys = [
            evaluation_key(point, node_count, integration_method, self.fingerprint, include_profiles)
            for point in points
        ]
        records: list[dict[str, object] | None] = [self.cache.get(key) for key in keys]
        pending: dict[str, tuple[int, np.ndarray]] = {}
        for index, (key, point, record) in enumerate(zip(keys, points, records, strict=True)):
            if record is None and key not in pending:
                pending[key] = (index, point)

        if pending:
            payloads = [
                {
                    "attachment1": str(self.attachment1),
                    "attachment2": str(self.attachment2),
                    "unit_point": point.tolist(),
                    "node_count": node_count,
                    "integration_method": integration_method,
                    "include_profiles": include_profiles,
                }
                for _, point in pending.values()
            ]
            if self.workers == 1:
                for number, payload in enumerate(payloads, start=1):
                    record = _run_payload(payload)
                    point = np.asarray(record["unit_point"], dtype=float)
                    key = evaluation_key(
                        point,
                        node_count,
                        integration_method,
                        self.fingerprint,
                        include_profiles,
                    )
                    self.cache.put(key, record)
                    print(
                        f"completed {number}/{len(payloads)} new {integration_method} evaluations",
                        flush=True,
                    )
            else:
                executor = ProcessPoolExecutor(max_workers=self.workers)
                payload_iterator = iter(payloads)
                active = {}
                try:
                    for _ in range(min(self.workers, len(payloads))):
                        payload = next(payload_iterator)
                        active[executor.submit(_run_payload, payload)] = payload
                    completed = 0
                    while active:
                        done, _ = wait(active, return_when=FIRST_COMPLETED)
                        for future in done:
                            active.pop(future)
                            record = future.result()
                            point = np.asarray(record["unit_point"], dtype=float)
                            key = evaluation_key(
                                point,
                                node_count,
                                integration_method,
                                self.fingerprint,
                                include_profiles,
                            )
                            self.cache.put(key, record)
                            completed += 1
                            print(
                                f"completed {completed}/{len(payloads)} new {integration_method} evaluations",
                                flush=True,
                            )
                            try:
                                payload = next(payload_iterator)
                            except StopIteration:
                                continue
                            active[executor.submit(_run_payload, payload)] = payload
                except BaseException:
                    for future in active:
                        future.cancel()
                    executor.shutdown(wait=False, cancel_futures=True)
                    raise
                else:
                    executor.shutdown(wait=True)

        output = []
        for key in keys:
            record = self.cache.get(key)
            if record is None:
                raise RuntimeError("evaluation cache unexpectedly missed a completed point")
            output.append(record)
        return output


def baseline_metadata() -> dict[str, object]:
    return {
        "reference_event_time_s": BASELINE_EVENT_TIME_S,
        "parameter_specs": [asdict(item) for item in PARAMETER_SPECS],
    }
