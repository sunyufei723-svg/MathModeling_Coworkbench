from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import platform
import subprocess
import sys
import time
from dataclasses import asdict, replace
from pathlib import Path

import numpy as np
import pandas as pd
import scipy

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "core"))
from environment import EnvironmentSeries, PostBoundary, post_boundary_from_tail
from radius import RadiusSeries
from scenarios import engineering_boundary_scenarios, mass_transfer_scenarios
from solver_bdf import SimulationResult, SolverConfig, solve_problem4_bdf
from solver_be import BEResult, BESolverConfig, solve_problem4_be


L1_REFERENCE_TIME_S = 182350
L2_REFERENCE_TIME_S = 182860


def json_dump(path: Path, value) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False), encoding="utf-8")


def finite_or_none(value: float):
    return float(value) if np.isfinite(value) else None


def load_inputs(attachment1: Path, attachment2: Path) -> tuple[EnvironmentSeries, RadiusSeries]:
    environment_frame = pd.read_excel(attachment1)
    radius_frame = pd.read_excel(attachment2)
    environment = EnvironmentSeries(
        environment_frame.iloc[:, 0].to_numpy(dtype=float),
        environment_frame.iloc[:, 1].to_numpy(dtype=float),
        environment_frame.iloc[:, 2].to_numpy(dtype=float),
    )
    radius = RadiusSeries(
        radius_frame.iloc[:, 0].to_numpy(dtype=float),
        radius_frame.iloc[:, 1].to_numpy(dtype=float),
        "linear",
    )
    return environment, radius


def timed_bdf(
    label: str,
    environment: EnvironmentSeries,
    radius: RadiusSeries,
    config: SolverConfig,
    post_boundary: PostBoundary | None = None,
) -> tuple[SimulationResult, float]:
    print(f"START BDF {label}", flush=True)
    started = time.perf_counter()
    result = solve_problem4_bdf(environment, radius, config, post_boundary)
    runtime = time.perf_counter() - started
    print(f"DONE  BDF {label}: {result.drying_event_time_s / 3600.0:.9f} h ({runtime:.2f} s)", flush=True)
    return result, runtime


def timed_be(
    label: str,
    environment: EnvironmentSeries,
    radius: RadiusSeries,
    config: BESolverConfig,
    post_boundary: PostBoundary | None = None,
) -> tuple[BEResult, float]:
    print(f"START BE  {label}", flush=True)
    started = time.perf_counter()
    result = solve_problem4_be(environment, radius, config, post_boundary)
    runtime = time.perf_counter() - started
    print(f"DONE  BE  {label}: {result.drying_event_time_s / 3600.0:.9f} h ({runtime:.2f} s)", flush=True)
    return result, runtime


def load_legacy_solver(path: Path, module_name: str):
    specification = importlib.util.spec_from_file_location(module_name, path)
    if specification is None or specification.loader is None:
        raise RuntimeError(f"cannot load legacy solver: {path}")
    module = importlib.util.module_from_spec(specification)
    sys.modules[module_name] = module
    specification.loader.exec_module(module)
    return module


def reproduce_legacy(
    project_root: Path,
    environment: EnvironmentSeries,
    radius: RadiusSeries,
) -> dict:
    cases = [
        ("L1", project_root / "code" / "submission" / "problem4" / "baselines" / "L1" / "solver.py", 201, L1_REFERENCE_TIME_S),
        (
            "L2",
            project_root / "code" / "submission" / "problem4" / "baselines" / "L2" / "solver.py",
            801,
            L2_REFERENCE_TIME_S,
        ),
    ]
    output = {}
    for label, path, node_count, expected in cases:
        module = load_legacy_solver(path, f"problem4_legacy_{label.lower()}")
        legacy_environment = module.EnvironmentSeries(
            environment.time_s,
            environment.temperature_c,
            environment.moisture,
        )
        legacy_radius = module.RadiusSeries(radius.time_s, radius.radius_cm)
        started = time.perf_counter()
        result = module.solve_problem4(
            legacy_environment,
            legacy_radius,
            module.SolverConfig(xi_points=node_count, dt_s=10.0),
        )
        runtime = time.perf_counter() - started
        actual = int(result.drying_end_time_s)
        if actual != expected:
            raise RuntimeError(f"{label} reproduction changed: {actual} != {expected}")
        output[label] = {
            "node_count": node_count,
            "time_step_s": 10.0,
            "event_time_s": actual,
            "event_time_h": actual / 3600.0,
            "runtime_s": runtime,
            "maximum_picard_iterations_used": int(np.max(result.coupling_iterations)),
            "unconverged_steps": int(np.count_nonzero(~result.coupling_converged)),
            "event_center_moisture": float(result.moisture[-1, 0]),
            "event_surface_moisture": float(result.moisture[-1, -1]),
        }
        print(f"REPRO {label}: {actual / 3600.0:.9f} h ({runtime:.2f} s)", flush=True)
    return output


def bdf_summary(result: SimulationResult, runtime_s: float) -> dict:
    return {
        "node_count": result.diagnostics.internal_node_count,
        "event_time_s": result.drying_event_time_s,
        "event_time_h": result.drying_event_time_s / 3600.0,
        "report_end_time_s": result.report_end_time_s,
        "event_radius_cm": result.event_radius_cm,
        "event_center_moisture": float(result.event_moisture_internal[0]),
        "event_surface_moisture": float(result.event_moisture_internal[-1]),
        "event_argmax_xi": float(np.argmax(result.event_moisture_internal) / (len(result.event_moisture_internal) - 1)),
        "runtime_s": runtime_s,
        "diagnostics": asdict(result.diagnostics),
    }


def be_summary(result: BEResult, runtime_s: float) -> dict:
    return {
        "node_count": len(result.event_moisture_internal),
        "event_time_s": result.drying_event_time_s,
        "event_time_h": result.drying_event_time_s / 3600.0,
        "event_radius_cm": result.event_radius_cm,
        "event_center_moisture": float(result.event_moisture_internal[0]),
        "event_surface_moisture": float(result.event_moisture_internal[-1]),
        "event_argmax_xi": float(np.argmax(result.event_moisture_internal) / (len(result.event_moisture_internal) - 1)),
        "runtime_s": runtime_s,
        "diagnostics": asdict(result.diagnostics),
    }


def common_profile_difference(
    left_times: np.ndarray,
    left_values: np.ndarray,
    right_times: np.ndarray,
    right_values: np.ndarray,
) -> float:
    common = sorted(set(left_times.astype(int)).intersection(right_times.astype(int)))
    common = [value for value in common if value % 21600 == 0]
    if not common:
        return float("inf")
    maximum = 0.0
    for time_s in common:
        left = left_values[int(np.where(np.isclose(left_times, time_s))[0][0])]
        right = right_values[int(np.where(np.isclose(right_times, time_s))[0][0])]
        finite = np.isfinite(left) & np.isfinite(right)
        if np.any(finite):
            maximum = max(maximum, float(np.max(np.abs(left[finite] - right[finite]))))
    return maximum


def compare_bdf(left: SimulationResult, right: SimulationResult) -> dict:
    difference_s = abs(left.drying_event_time_s - right.drying_event_time_s)
    return {
        "event_time_difference_s": difference_s,
        "event_time_relative_difference": difference_s / right.drying_event_time_s,
        "paper_sample_maximum_moisture_difference": common_profile_difference(
            left.time_s, left.moisture, right.time_s, right.moisture
        ),
        "event_location_same": bool(
            np.argmax(left.event_moisture_internal) == 0 and np.argmax(right.event_moisture_internal) == 0
        ),
    }


def compare_bdf_be(left: SimulationResult, right: BEResult) -> dict:
    difference_s = abs(left.drying_event_time_s - right.drying_event_time_s)
    return {
        "event_time_difference_s": difference_s,
        "event_time_relative_difference": difference_s / left.drying_event_time_s,
        "paper_sample_maximum_moisture_difference": common_profile_difference(
            left.time_s, left.moisture, right.time_s, right.moisture
        ),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="运行问题四 L3 严格 FVM+BDF 全量验证")
    parser.add_argument("--attachment1", type=Path, required=True)
    parser.add_argument("--attachment2", type=Path, required=True)
    parser.add_argument("--project-root", type=Path, required=True)
    parser.add_argument("--work-dir", type=Path, required=True)
    parser.add_argument("--results-dir", type=Path, required=True)
    parser.add_argument("--resume", action="store_true", help="复用已写入work目录的基准/情景断点")
    args = parser.parse_args()
    args.work_dir.mkdir(parents=True, exist_ok=True)
    args.results_dir.mkdir(parents=True, exist_ok=True)
    environment, radius = load_inputs(args.attachment1, args.attachment2)

    baseline_checkpoint = args.work_dir / "baseline_reproduction.json"
    if args.resume and baseline_checkpoint.exists():
        baseline = json.loads(baseline_checkpoint.read_text(encoding="utf-8"))
        print("RESUME legacy L1/L2 reproduction", flush=True)
    else:
        baseline = reproduce_legacy(args.project_root, environment, radius)
        json_dump(baseline_checkpoint, baseline)

    base_bdf = SolverConfig(
        node_count=201,
        sample_interval_s=21600,
        relative_tolerance=1.0e-8,
        temperature_absolute_tolerance=1.0e-8,
        moisture_absolute_tolerance=1.0e-10,
        max_time_step_s=30.0,
    )
    spatial_node_counts = [201, 401, 801, 1601]
    spatial_results: dict[int, SimulationResult] = {}
    spatial_rows = []
    previous_event = None
    for node_count in spatial_node_counts:
        result, runtime = timed_bdf(
            f"spatial n={node_count}", environment, radius, replace(base_bdf, node_count=node_count)
        )
        spatial_results[node_count] = result
        row = bdf_summary(result, runtime)
        row["difference_from_previous_s"] = (
            None if previous_event is None else result.drying_event_time_s - previous_event
        )
        spatial_rows.append(row)
        previous_event = result.drying_event_time_s
        json_dump(args.work_dir / "spatial_progress.json", spatial_rows)

    spatial_pairs = []
    for coarse, fine in zip(spatial_node_counts[:-1], spatial_node_counts[1:], strict=True):
        metrics = compare_bdf(spatial_results[coarse], spatial_results[fine])
        metrics.update({"coarse_node_count": coarse, "fine_node_count": fine})
        metrics["accepted"] = bool(
            metrics["event_time_difference_s"] < 60.0
            and metrics["event_time_relative_difference"] < 1.0e-3
            and metrics["paper_sample_maximum_moisture_difference"] < 5.0e-5
            and metrics["event_location_same"]
        )
        spatial_pairs.append(metrics)
    if not spatial_pairs[-1]["accepted"]:
        node_count = 3201
        result, runtime = timed_bdf(
            f"spatial n={node_count}", environment, radius, replace(base_bdf, node_count=node_count)
        )
        spatial_results[node_count] = result
        row = bdf_summary(result, runtime)
        row["difference_from_previous_s"] = result.drying_event_time_s - previous_event
        spatial_rows.append(row)
        metrics = compare_bdf(spatial_results[1601], result)
        metrics.update({"coarse_node_count": 1601, "fine_node_count": 3201})
        metrics["accepted"] = bool(
            metrics["event_time_difference_s"] < 60.0
            and metrics["event_time_relative_difference"] < 1.0e-3
            and metrics["paper_sample_maximum_moisture_difference"] < 5.0e-5
            and metrics["event_location_same"]
        )
        spatial_pairs.append(metrics)
        spatial_node_counts.append(node_count)
    selected_node_count = spatial_node_counts[-1]
    if not spatial_pairs[-1]["accepted"]:
        raise RuntimeError(f"finest spatial pair did not pass: {spatial_pairs[-1]}")

    bdf_configs = {
        "B1": replace(
            base_bdf,
            node_count=selected_node_count,
            relative_tolerance=1.0e-7,
            temperature_absolute_tolerance=1.0e-7,
            moisture_absolute_tolerance=1.0e-9,
            max_time_step_s=60.0,
        ),
        "B2": replace(base_bdf, node_count=selected_node_count),
        "B3": replace(
            base_bdf,
            node_count=selected_node_count,
            relative_tolerance=1.0e-9,
            temperature_absolute_tolerance=1.0e-10,
            moisture_absolute_tolerance=1.0e-12,
            max_time_step_s=10.0,
        ),
    }
    bdf_results: dict[str, SimulationResult] = {"B2": spatial_results[selected_node_count]}
    bdf_runtime = {"B2": spatial_rows[-1]["runtime_s"]}
    for name in ("B1", "B3"):
        bdf_results[name], bdf_runtime[name] = timed_bdf(
            f"time {name}", environment, radius, bdf_configs[name]
        )
    bdf_rows = [
        {"name": name, "config": asdict(bdf_configs[name]), **bdf_summary(bdf_results[name], bdf_runtime[name])}
        for name in ("B1", "B2", "B3")
    ]
    bdf_comparisons = {
        "B1_vs_B2": compare_bdf(bdf_results["B1"], bdf_results["B2"]),
        "B2_vs_B3": compare_bdf(bdf_results["B2"], bdf_results["B3"]),
    }
    bdf_pass = bool(
        bdf_comparisons["B2_vs_B3"]["event_time_difference_s"] < 10.0
        and bdf_comparisons["B2_vs_B3"]["paper_sample_maximum_moisture_difference"] < 1.0e-4
    )

    be_results: dict[float, BEResult] = {}
    be_rows = []
    for dt_s in (20.0, 10.0, 5.0, 2.5):
        config = BESolverConfig(node_count=selected_node_count, time_step_s=dt_s, sample_interval_s=21600)
        result, runtime = timed_be(f"time dt={dt_s:g}s", environment, radius, config)
        be_results[dt_s] = result
        be_rows.append({"dt_s": dt_s, "config": asdict(config), **be_summary(result, runtime)})
        json_dump(args.work_dir / "be_progress.json", be_rows)
    be_pairs = [
        {
            "coarse_dt_s": coarse,
            "fine_dt_s": fine,
            "event_time_difference_s": abs(be_results[coarse].drying_event_time_s - be_results[fine].drying_event_time_s),
            "paper_sample_maximum_moisture_difference": common_profile_difference(
                be_results[coarse].time_s,
                be_results[coarse].moisture,
                be_results[fine].time_s,
                be_results[fine].moisture,
            ),
        }
        for coarse, fine in ((20.0, 10.0), (10.0, 5.0), (5.0, 2.5))
    ]
    be_pass = bool(
        be_pairs[-1]["event_time_difference_s"] < 30.0
        and be_pairs[-1]["paper_sample_maximum_moisture_difference"] < 1.0e-4
        and all(row["diagnostics"]["unconverged_steps"] == 0 for row in be_rows)
    )
    cross_solver = compare_bdf_be(bdf_results["B3"], be_results[2.5])
    cross_pass = bool(
        cross_solver["event_time_difference_s"] < 60.0
        and cross_solver["paper_sample_maximum_moisture_difference"] < 1.0e-4
    )

    ablation = [
        {
            "experiment": "A0",
            "geometry": "L1近似",
            "d_mean": "arithmetic",
            "k_mean": "arithmetic",
            "time_method": "BE 10 s",
            "event_time_s": baseline["L1"]["event_time_s"],
            "event_time_h": baseline["L1"]["event_time_h"],
            "difference_from_previous_s": None,
        }
    ]
    previous_time = baseline["L1"]["event_time_s"]
    for name, d_mean, k_mean in (
        ("A1", "arithmetic", "arithmetic"),
        ("A2", "harmonic", "arithmetic"),
        ("A3", "harmonic", "harmonic"),
    ):
        config = BESolverConfig(
            node_count=201,
            time_step_s=10.0,
            d_interface_mean=d_mean,
            k_interface_mean=k_mean,
            sample_interval_s=21600,
        )
        result, runtime = timed_be(f"ablation {name}", environment, radius, config)
        row = {
            "experiment": name,
            "geometry": "strict FVM",
            "d_mean": d_mean,
            "k_mean": k_mean,
            "time_method": "BE 10 s",
            **be_summary(result, runtime),
            "difference_from_previous_s": result.drying_event_time_s - previous_time,
        }
        ablation.append(row)
        previous_time = result.drying_event_time_s
    main_reference = bdf_results["B2"]
    ablation_bdf_reference = spatial_results[201]
    ablation.append(
        {
            "experiment": "A4",
            "geometry": "strict FVM",
            "d_mean": "harmonic",
            "k_mean": "harmonic",
            "time_method": "adaptive BDF",
            **bdf_summary(ablation_bdf_reference, spatial_rows[0]["runtime_s"]),
            "difference_from_previous_s": ablation_bdf_reference.drying_event_time_s - previous_time,
        }
    )

    default_post = post_boundary_from_tail(environment)
    scenario_config = bdf_configs["B2"]
    cache: dict[tuple, tuple[SimulationResult, float]] = {
        (default_post.temperature_c, default_post.moisture, 1.0): (main_reference, bdf_runtime["B2"])
    }
    boundary_checkpoint_path = args.work_dir / "boundary_progress.json"
    boundary_checkpoint: dict[str, dict] = {}
    if args.resume and boundary_checkpoint_path.exists():
        boundary_checkpoint = json.loads(boundary_checkpoint_path.read_text(encoding="utf-8"))

    def scenario_run(name: str, post: PostBoundary, hm_factor: float):
        if name in boundary_checkpoint:
            print(f"RESUME boundary {name}", flush=True)
            return boundary_checkpoint[name]
        key = (round(post.temperature_c, 12), round(post.moisture, 12), hm_factor)
        if key not in cache:
            cache[key] = timed_bdf(
                f"boundary {name}",
                environment,
                radius,
                replace(scenario_config, mass_transfer_m_s=scenario_config.mass_transfer_m_s * hm_factor),
                post,
            )
        result, runtime = cache[key]
        row = {
            "scenario": name,
            "post_temperature_c": post.temperature_c,
            "post_moisture": post.moisture,
            "mass_transfer_factor": hm_factor,
            **bdf_summary(result, runtime),
            "difference_from_default_s": result.drying_event_time_s - main_reference.drying_event_time_s,
        }
        boundary_checkpoint[name] = row
        json_dump(boundary_checkpoint_path, boundary_checkpoint)
        return row

    data_rows = [
        scenario_run("attachment_terminal_value", default_post, 1.0),
        scenario_run("last_30_min_time_average", post_boundary_from_tail(environment, 1800.0), 1.0),
        scenario_run("last_1_h_time_average", post_boundary_from_tail(environment, 3600.0), 1.0),
    ]
    engineering_rows = [
        scenario_run(item.name, item.post_boundary, item.mass_transfer_factor)
        for item in engineering_boundary_scenarios(default_post)
    ]
    hm_rows = [
        scenario_run(item.name, item.post_boundary, item.mass_transfer_factor)
        for item in mass_transfer_scenarios(default_post)
    ]
    boundary_times = [row["event_time_s"] for row in data_rows + engineering_rows + hm_rows]

    special_checkpoint_path = args.work_dir / "special_sensitivity_progress.json"
    special = {}
    if args.resume and special_checkpoint_path.exists():
        special = json.loads(special_checkpoint_path.read_text(encoding="utf-8"))

    if "pchip" not in special:
        pchip_result, pchip_runtime = timed_bdf(
            "radius PCHIP", environment, radius.with_interpolation("pchip"), scenario_config
        )
        special["pchip"] = bdf_summary(pchip_result, pchip_runtime)
        json_dump(special_checkpoint_path, special)
    else:
        print("RESUME radius PCHIP", flush=True)

    if "fixed_radius" not in special:
        fixed_result, fixed_runtime = timed_bdf(
            "fixed radius 2 cm",
            environment,
            radius,
            replace(
                scenario_config,
                fixed_radius_cm=2.0,
                initial_time_limit_s=120.0 * 3600.0,
                fallback_time_limit_s=168.0 * 3600.0,
            ),
        )
        special["fixed_radius"] = bdf_summary(fixed_result, fixed_runtime)
        json_dump(special_checkpoint_path, special)
    else:
        print("RESUME fixed radius", flush=True)

    if "eulerian" not in special:
        eulerian_result, eulerian_runtime = timed_bdf(
            "Eulerian model form", environment, radius, replace(scenario_config, model_form="eulerian")
        )
        special["eulerian"] = bdf_summary(eulerian_result, eulerian_runtime)
        json_dump(special_checkpoint_path, special)
    else:
        print("RESUME Eulerian model form", flush=True)

    print("START final 60 s output run", flush=True)
    final_result, final_runtime = timed_bdf(
        "final output", environment, radius, replace(scenario_config, sample_interval_s=60)
    )
    if abs(final_result.drying_event_time_s - main_reference.drying_event_time_s) > 1.0e-6:
        raise RuntimeError("sampling interval changed the continuous solution")

    quality_pass = bool(
        final_result.diagnostics.maximum_normalized_balance_residual < 1.0e-6
        and final_result.diagnostics.minimum_raw_moisture >= -1.0e-8
        and final_result.diagnostics.radial_monotonicity_all_outputs
        and np.argmax(final_result.event_moisture_internal) == 0
        and final_result.previous_report_max_moisture >= 0.15 - 1.0e-10
        and final_result.report_max_moisture < 0.15
    )

    verification = {
        "source": {
            "git_commit_at_start": subprocess.run(
                ["git", "rev-parse", "HEAD"],
                cwd=args.project_root,
                check=True,
                capture_output=True,
                text=True,
            ).stdout.strip(),
            "attachment1_sha256": hashlib.sha256(args.attachment1.read_bytes()).hexdigest(),
            "attachment2_sha256": hashlib.sha256(args.attachment2.read_bytes()).hexdigest(),
            "environment_terminal_time_s": environment.terminal_time_s,
            "environment_terminal_temperature_c": environment.terminal_temperature_c,
            "environment_terminal_moisture": environment.terminal_moisture,
            "radius_terminal_time_s": radius.terminal_time_s,
            "radius_initial_cm": float(radius.radius_cm[0]),
            "radius_terminal_cm": float(radius.radius_cm[-1]),
            "python_version": platform.python_version(),
            "numpy_version": np.__version__,
            "scipy_version": scipy.__version__,
            "pandas_version": pd.__version__,
        },
        "baseline": baseline,
        "ablation": ablation,
        "spatial_grid": {
            "runs": spatial_rows,
            "adjacent_comparisons": spatial_pairs,
            "selected_node_count": selected_node_count,
            "passed": bool(spatial_pairs[-1]["accepted"]),
            "oscillatory": bool(
                len(spatial_rows) >= 3
                and np.sign(spatial_rows[-1]["difference_from_previous_s"])
                != np.sign(spatial_rows[-2]["difference_from_previous_s"])
            ),
        },
        "bdf_time_sensitivity": {"runs": bdf_rows, "comparisons": bdf_comparisons, "passed": bdf_pass},
        "be_time_sensitivity": {"runs": be_rows, "comparisons": be_pairs, "passed": be_pass},
        "cross_solver": {"comparison": cross_solver, "passed": cross_pass},
        "boundary_sensitivity": {
            "data_driven": data_rows,
            "engineering_3x3": engineering_rows,
            "mass_transfer": hm_rows,
            "all_scenarios_range_s": [float(min(boundary_times)), float(max(boundary_times))],
            "all_scenarios_range_h": [float(min(boundary_times) / 3600.0), float(max(boundary_times) / 3600.0)],
        },
        "radius_sensitivity": {
            "linear_event_time_s": main_reference.drying_event_time_s,
            "linear_event_time_h": main_reference.drying_event_time_s / 3600.0,
            "pchip_event_time_s": special["pchip"]["event_time_s"],
            "pchip_event_time_h": special["pchip"]["event_time_h"],
            "absolute_difference_s": abs(special["pchip"]["event_time_s"] - main_reference.drying_event_time_s),
            "pchip_runtime_s": special["pchip"]["runtime_s"],
        },
        "shrinkage_ablation": {
            "fixed_radius_event_time_s": special["fixed_radius"]["event_time_s"],
            "fixed_radius_event_time_h": special["fixed_radius"]["event_time_h"],
            "dynamic_radius_event_time_s": main_reference.drying_event_time_s,
            "dynamic_radius_event_time_h": main_reference.drying_event_time_s / 3600.0,
            "time_reduction_s": special["fixed_radius"]["event_time_s"] - main_reference.drying_event_time_s,
            "time_reduction_h": (special["fixed_radius"]["event_time_s"] - main_reference.drying_event_time_s) / 3600.0,
            "fixed_radius_runtime_s": special["fixed_radius"]["runtime_s"],
        },
        "model_form_sensitivity": {
            "material_event_time_s": main_reference.drying_event_time_s,
            "material_event_time_h": main_reference.drying_event_time_s / 3600.0,
            "eulerian_event_time_s": special["eulerian"]["event_time_s"],
            "eulerian_event_time_h": special["eulerian"]["event_time_h"],
            "absolute_difference_s": abs(special["eulerian"]["event_time_s"] - main_reference.drying_event_time_s),
            "absolute_difference_h": abs(special["eulerian"]["event_time_s"] - main_reference.drying_event_time_s) / 3600.0,
            "eulerian_runtime_s": special["eulerian"]["runtime_s"],
        },
        "final": {
            "all_numerical_acceptance_checks_passed": bool(
                spatial_pairs[-1]["accepted"] and bdf_pass and be_pass and cross_pass and quality_pass
            ),
            "selected_node_count": selected_node_count,
            "bdf_configuration": "B2",
            "continuous_event_time_s": final_result.drying_event_time_s,
            "continuous_event_time_h": final_result.drying_event_time_s / 3600.0,
            "first_strict_60s_time_s": final_result.report_end_time_s,
            "first_strict_60s_time_h": final_result.report_end_time_s / 3600.0,
            "previous_report_time_s": final_result.previous_report_time_s,
            "previous_max_moisture": final_result.previous_report_max_moisture,
            "event_max_moisture": float(np.max(final_result.event_moisture_internal)),
            "first_strict_report_max_moisture": final_result.report_max_moisture,
            "event_center_moisture": float(final_result.event_moisture_internal[0]),
            "event_surface_moisture": float(final_result.event_moisture_internal[-1]),
            "event_radius_cm": final_result.event_radius_cm,
            "argmax_location_xi": float(np.argmax(final_result.event_moisture_internal) / (selected_node_count - 1)),
            "minimum_raw_moisture": final_result.diagnostics.minimum_raw_moisture,
            "clip_diagnostics": {
                "clipped_cell_count": final_result.diagnostics.clipped_cell_count,
                "maximum_clip_magnitude": final_result.diagnostics.maximum_clip_magnitude,
            },
            "maximum_normalized_balance_residual": final_result.diagnostics.maximum_normalized_balance_residual,
            "dry_mass_index_relative_range": final_result.diagnostics.dry_mass_index_relative_range,
            "boundary_all_scenarios_range_h": [
                float(min(boundary_times) / 3600.0),
                float(max(boundary_times) / 3600.0),
            ],
            "final_output_runtime_s": final_runtime,
            "quality_checks_passed": quality_pass,
        },
    }
    json_dump(args.results_dir / "verification.json", verification)

    headers = [
        "时间\\到药材中心的距离",
        *[float(value) for value in final_result.fixed_distance_cm],
        "药材表面",
    ]
    rows = []
    for time_s, values in zip(final_result.time_s, final_result.moisture, strict=True):
        rows.append([int(round(time_s)), *[finite_or_none(float(value)) for value in values]])
    payload = {"headers": headers, "rows": rows, "metadata": verification["final"]}
    json_dump(args.work_dir / "result4_payload.json", payload)
    def _ok(passed: bool) -> str:
        return "通过" if passed else "未通过"

    final = verification["final"]
    boundary = verification["boundary_sensitivity"]
    bar = "=" * 64
    print(bar, flush=True)
    print("问题四 L3 严格 FVM+BDF —— 运行与验证结果汇总", flush=True)
    print(bar, flush=True)
    print(f"[主答案] 连续临界时间 t* = {final['continuous_event_time_h']:.6f} h ({final['continuous_event_time_s']:.3f} s)", flush=True)
    print(f"[主答案] 首个严格达标 60 s 时刻 = {final['first_strict_60s_time_h']:.6f} h", flush=True)
    print(f"[主答案] 后期边界全部情景范围 = {boundary['all_scenarios_range_h'][0]:.4f}-{boundary['all_scenarios_range_h'][1]:.4f} h", flush=True)
    print("-" * 64, flush=True)
    print("[空间网格收敛]", flush=True)
    for row in verification["spatial_grid"]["runs"]:
        diff = row.get("difference_from_previous_s")
        diff_s = "--" if diff is None else f"{diff:+.3f} s"
        print(f"  N={row['node_count']:>5}: t*={row['event_time_h']:.9f} h  (相邻差 {diff_s}, {row['runtime_s']:.1f} s)", flush=True)
    print(f"  相邻网格验收：{_ok(verification['spatial_grid']['passed'])}", flush=True)
    print("[BDF 容差/步长敏感性]", flush=True)
    for row in verification["bdf_time_sensitivity"]["runs"]:
        print(f"  {row['name']}: rtol={row['config']['relative_tolerance']:.0e} max_step={row['config']['max_time_step_s']:g}s -> t*={row['event_time_h']:.9f} h", flush=True)
    print(f"  BDF 时间敏感性：{_ok(verification['bdf_time_sensitivity']['passed'])}", flush=True)
    print("[后向欧拉交叉验证]", flush=True)
    for row in verification["be_time_sensitivity"]["runs"]:
        print(f"  dt={row['dt_s']:g}s -> t*={row['event_time_h']:.9f} h (Picard max {row['diagnostics']['maximum_picard_iterations_used']}, 未收敛步 {row['diagnostics']['unconverged_steps']})", flush=True)
    print(f"  BE 时间敏感性：{_ok(verification['be_time_sensitivity']['passed'])}；BDF/BE 交叉：{_ok(verification['cross_solver']['passed'])}", flush=True)
    print("[后期边界情景敏感性]", flush=True)
    for row in boundary["data_driven"] + boundary["engineering_3x3"] + boundary["mass_transfer"]:
        print(f"  {row['scenario']}: T={row['post_temperature_c']:.4f}C C={row['post_moisture']:.4f} hm x{row['mass_transfer_factor']:.1f} -> t*={row['event_time_h']:.6f} h ({row['difference_from_default_s']/60.0:+.2f} min)", flush=True)
    rad = verification["radius_sensitivity"]
    print(f"[半径插值] linear={rad['linear_event_time_h']:.9f} h  pchip={rad['pchip_event_time_h']:.9f} h  差={rad['absolute_difference_s']:.3f} s", flush=True)
    sh = verification["shrinkage_ablation"]
    print(f"[收缩消融] 动态半径={sh['dynamic_radius_event_time_h']:.6f} h  固定2cm={sh['fixed_radius_event_time_h']:.6f} h  缩短={sh['time_reduction_h']:.6f} h", flush=True)
    mf = verification["model_form_sensitivity"]
    print(f"[坐标模型形式] 物质坐标={mf['material_event_time_h']:.6f} h  Euler={mf['eulerian_event_time_h']:.6f} h  差={mf['absolute_difference_h']:.6f} h", flush=True)
    print("[基准对照 L1-L4]", flush=True)
    print(f"  L1(原近似/算术/201/BE10s) = {verification['baseline']['L1']['event_time_h']:.6f} h", flush=True)
    print(f"  L2(原近似/D调和/801/BE10s) = {verification['baseline']['L2']['event_time_h']:.6f} h", flush=True)
    print(f"  L3(严格FVM/调和/自适应BDF) = {final['continuous_event_time_h']:.6f} h  <- 主答案", flush=True)
    print(f"  L4(Euler含收缩输运项)      = {mf['eulerian_event_time_h']:.6f} h", flush=True)
    print("[数值消融 A0-A4]", flush=True)
    for row in verification["ablation"]:
        d = row.get("difference_from_previous_s")
        d_s = "--" if d is None else f"{d/60.0:+.2f} min"
        print(f"  {row['experiment']} {row['geometry']}/D:{row['d_mean']}/k:{row['k_mean']}/{row['time_method']} -> {row['event_time_h']:.6f} h ({d_s})", flush=True)
    print("-" * 64, flush=True)
    print(f"[守恒核验] 最大归一化通量残差={final['maximum_normalized_balance_residual']:.3e}  最小原始含水率={final['minimum_raw_moisture']:.9f} kg/kg", flush=True)
    print(f"[干物质诊断] 相对变幅={final['dry_mass_index_relative_range']:.2%}（模型局限指标，非失败判据）", flush=True)
    print(f"[总验收] 全部数值验收：{_ok(final['all_numerical_acceptance_checks_passed'])}", flush=True)
    print(bar, flush=True)
    print(f"已写出：{args.results_dir / 'verification.json'}（结构化验证，兼画图数据源）、{args.work_dir / 'result4_payload.json'}（供 export_result4.mjs 生成 result4.xlsx）", flush=True)


if __name__ == "__main__":
    main()
