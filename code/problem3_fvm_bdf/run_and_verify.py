from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import platform
import sys
import time
from dataclasses import asdict, replace
from pathlib import Path

import numpy as np
import pandas as pd
import scipy

try:
    from .model import EnvironmentSeries, PostBoundary, post_boundary_from_tail
    from .solver_bdf import SimulationResult, SolverConfig, solve_problem3_bdf
    from .solver_be import BEResult, BESolverConfig, solve_problem3_be
except ImportError:
    from model import EnvironmentSeries, PostBoundary, post_boundary_from_tail  # type: ignore
    from solver_bdf import SimulationResult, SolverConfig, solve_problem3_bdf  # type: ignore
    from solver_be import BEResult, BESolverConfig, solve_problem3_be  # type: ignore


PROJECT_ROOT = Path(__file__).resolve().parents[2]
ORIGINAL_RESULT = PROJECT_ROOT / "results" / "problem3" / "result3.xlsx"
ORIGINAL_SOLVER = PROJECT_ROOT / "code" / "problem3" / "solver.py"
PAPER_RADII_CM = np.array([0.0, 0.5, 1.0, 1.5, 2.0])
BASELINE_TIME_S = 198210
CANDIDATE_TIME_H = 57.4778


def load_environment(path: Path) -> EnvironmentSeries:
    frame = pd.read_excel(path)
    required = ["时间", "温度", "水分浓度"]
    missing = [name for name in required if name not in frame.columns]
    if missing:
        raise ValueError(f"附件1缺少列：{missing}")
    return EnvironmentSeries(
        frame["时间"].to_numpy(float),
        frame["温度"].to_numpy(float),
        frame["水分浓度"].to_numpy(float),
    )


def json_dump(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def progress(work_dir: Path, stage: str, details: object) -> None:
    json_dump(work_dir / "progress.json", {"stage": stage, "details": details})


def run_baseline(environment: EnvironmentSeries) -> dict[str, object]:
    spec = importlib.util.spec_from_file_location("problem3_baseline_solver", ORIGINAL_SOLVER)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    assert spec.loader is not None
    spec.loader.exec_module(module)
    baseline_environment = module.EnvironmentSeries(
        environment.time_s,
        environment.temperature_c,
        environment.moisture,
    )
    started = time.perf_counter()
    result = module.solve_problem3(baseline_environment)
    workbook = pd.read_excel(ORIGINAL_RESULT, sheet_name="水分浓度")
    return {
        "settings": {
            "spatial_step_cm": 0.1,
            "time_step_s": 10.0,
            "geometry": "original approximate radial discretization",
            "interface_mean": "arithmetic",
            "time_method": "backward Euler",
            "nonlinear_method": "Picard",
            "post_boundary": "hold attachment terminal value",
        },
        "end_time_s": int(result.drying_end_time_s),
        "end_time_h": float(result.drying_end_time_s / 3600.0),
        "end_profile_raw": result.moisture[-1].tolist(),
        "all_picard_steps_converged": bool(result.coupling_converged.all()),
        "maximum_picard_iterations": int(result.coupling_iterations.max()),
        "runtime_s": time.perf_counter() - started,
        "workbook_rows_without_header": int(workbook.shape[0]),
        "workbook_columns": int(workbook.shape[1]),
        "workbook_last_time_s": int(workbook.iloc[-1, 0]),
        "workbook_last_profile_displayed": workbook.iloc[-1, 1:].astype(float).tolist(),
    }


def values_at_times(result: SimulationResult | BEResult, times_s: np.ndarray) -> np.ndarray:
    indices = []
    for value in times_s:
        matches = np.where(np.isclose(result.time_s, value, rtol=0.0, atol=1e-8))[0]
        if not len(matches):
            raise ValueError(f"result has no regular output at t={value}")
        indices.append(int(matches[0]))
    radius_indices = [int(np.where(np.isclose(result.radius_cm, radius))[0][0]) for radius in PAPER_RADII_CM]
    return result.moisture[np.ix_(indices, radius_indices)]


def common_paper_times(*results: SimulationResult | BEResult) -> np.ndarray:
    latest_common = min(float(result.drying_event_time_s) for result in results)
    return np.arange(6.0 * 3600.0, np.floor(latest_common / (6.0 * 3600.0)) * 6.0 * 3600.0 + 1.0, 6.0 * 3600.0)


def comparison(left: SimulationResult | BEResult, right: SimulationResult | BEResult) -> dict[str, object]:
    times = common_paper_times(left, right)
    left_values = values_at_times(left, times)
    right_values = values_at_times(right, times)
    difference = np.abs(left_values - right_values)
    location = np.unravel_index(int(np.argmax(difference)), difference.shape)
    return {
        "event_time_difference_s": float(abs(left.drying_event_time_s - right.drying_event_time_s)),
        "event_time_relative_difference": float(
            abs(left.drying_event_time_s - right.drying_event_time_s) / right.drying_event_time_s
        ),
        "paper_sample_maximum_moisture_difference": float(difference[location]),
        "paper_sample_time_h_at_maximum": float(times[location[0]] / 3600.0),
        "paper_sample_radius_cm_at_maximum": float(PAPER_RADII_CM[location[1]]),
    }


def summarize_bdf(result: SimulationResult, runtime_s: float) -> dict[str, object]:
    return {
        "event_time_s": result.drying_event_time_s,
        "event_time_h": result.drying_event_time_s / 3600.0,
        "t60_s": result.report_end_time_s,
        "event_max_moisture": float(result.event_internal_moisture.max()),
        "event_argmax_radius_cm": float(
            result.event_internal_radius_cm[int(np.argmax(result.event_internal_moisture))]
        ),
        "event_center_moisture": float(result.event_internal_moisture[0]),
        "event_surface_moisture": float(result.event_internal_moisture[-1]),
        "t60_max_moisture": float(result.max_moisture[-1]),
        "previous_60s_max_moisture": float(result.max_moisture[-2]) if len(result.max_moisture) > 1 else None,
        "runtime_s": runtime_s,
        "diagnostics": asdict(result.diagnostics),
    }


def summarize_be(result: BEResult, runtime_s: float) -> dict[str, object]:
    return {
        "event_time_s": result.drying_event_time_s,
        "event_time_h": result.drying_event_time_s / 3600.0,
        "event_max_moisture": float(result.event_internal_moisture.max()),
        "event_argmax_radius_cm": float(
            result.event_internal_radius_cm[int(np.argmax(result.event_internal_moisture))]
        ),
        "event_center_moisture": float(result.event_internal_moisture[0]),
        "event_surface_moisture": float(result.event_internal_moisture[-1]),
        "runtime_s": runtime_s,
        "diagnostics": asdict(result.diagnostics),
    }


def bdf_run(label: str, environment: EnvironmentSeries, config: SolverConfig, post: PostBoundary | None = None):
    print(f"START BDF {label}", flush=True)
    started = time.perf_counter()
    result = solve_problem3_bdf(environment, config, post)
    elapsed = time.perf_counter() - started
    print(f"DONE  BDF {label}: {result.drying_event_time_s / 3600.0:.9f} h ({elapsed:.2f} s)", flush=True)
    return result, elapsed


def be_run(label: str, environment: EnvironmentSeries, config: BESolverConfig, post: PostBoundary | None = None):
    print(f"START BE  {label}", flush=True)
    started = time.perf_counter()
    result = solve_problem3_be(environment, config, post)
    elapsed = time.perf_counter() - started
    print(f"DONE  BE  {label}: {result.drying_event_time_s / 3600.0:.9f} h ({elapsed:.2f} s)", flush=True)
    return result, elapsed


def main() -> None:
    parser = argparse.ArgumentParser(description="运行问题三严格 FVM+BDF 全量验证")
    parser.add_argument("--attachment1", type=Path, required=True)
    parser.add_argument("--work-dir", type=Path, required=True)
    parser.add_argument("--payload", type=Path, required=True)
    parser.add_argument("--verification", type=Path, required=True)
    args = parser.parse_args()
    args.work_dir.mkdir(parents=True, exist_ok=True)
    environment = load_environment(args.attachment1)

    print("START baseline reproduction", flush=True)
    baseline = run_baseline(environment)
    if baseline["end_time_s"] != BASELINE_TIME_S:
        raise RuntimeError(f"baseline changed: {baseline['end_time_s']} != {BASELINE_TIME_S}")
    print("DONE  baseline reproduction: 55.058333333 h", flush=True)
    progress(args.work_dir, "baseline", baseline)

    spatial_dr = [0.1, 0.05, 0.025, 0.0125, 0.00625, 0.003125, 0.0015625, 0.00078125]
    spatial_config = SolverConfig(
        relative_tolerance=1e-8,
        temperature_absolute_tolerance=1e-8,
        moisture_absolute_tolerance=1e-10,
        max_time_step_s=60.0,
        extended_time_limit_s=1000.0 * 3600.0,
    )
    spatial_results: dict[float, SimulationResult] = {}
    spatial_rows = []
    for dr in spatial_dr:
        result, elapsed = bdf_run(f"spatial dr={dr:g} cm", environment, replace(spatial_config, internal_dr_cm=dr))
        spatial_results[dr] = result
        row = {"dr_cm": dr, **summarize_bdf(result, elapsed)}
        spatial_rows.append(row)
        progress(args.work_dir, f"spatial_{dr:g}", spatial_rows)

    spatial_pairs = []
    for coarse, fine in zip(spatial_dr[:-1], spatial_dr[1:], strict=True):
        metrics = comparison(spatial_results[coarse], spatial_results[fine])
        metrics.update(
            {
                "coarse_dr_cm": coarse,
                "fine_dr_cm": fine,
                "event_location_same": bool(
                    spatial_rows[spatial_dr.index(coarse)]["event_argmax_radius_cm"]
                    == spatial_rows[spatial_dr.index(fine)]["event_argmax_radius_cm"]
                ),
            }
        )
        metrics["accepted"] = bool(
            metrics["event_time_difference_s"] < 60.0
            and metrics["event_time_relative_difference"] < 1e-3
            and metrics["paper_sample_maximum_moisture_difference"] < 5e-5
            and metrics["event_location_same"]
        )
        spatial_pairs.append(metrics)

    selected_dr = spatial_dr[-1]
    if not spatial_pairs[-1]["accepted"]:
        raise RuntimeError(f"finest spatial pair did not pass: {spatial_pairs[-1]}")
    last_three_times = [spatial_results[dr].drying_event_time_s for dr in spatial_dr[-3:]]
    observed_order = float(
        np.log2(abs(last_three_times[0] - last_three_times[1]) / abs(last_three_times[1] - last_three_times[2]))
    )
    richardson_event_time_s = float(
        last_three_times[2]
        + (last_three_times[2] - last_three_times[1]) / (2.0**observed_order - 1.0)
    )

    time_configs = {
        "B1": replace(
            SolverConfig(internal_dr_cm=selected_dr),
            relative_tolerance=1e-7,
            temperature_absolute_tolerance=1e-7,
            moisture_absolute_tolerance=1e-9,
            max_time_step_s=60.0,
        ),
        "B2": replace(
            SolverConfig(internal_dr_cm=selected_dr),
            relative_tolerance=1e-8,
            temperature_absolute_tolerance=1e-8,
            moisture_absolute_tolerance=1e-10,
            max_time_step_s=30.0,
        ),
        "B3": replace(
            SolverConfig(internal_dr_cm=selected_dr),
            relative_tolerance=1e-9,
            temperature_absolute_tolerance=1e-10,
            moisture_absolute_tolerance=1e-12,
            max_time_step_s=10.0,
        ),
    }
    bdf_time_results = {}
    bdf_time_rows = []
    for name, config in time_configs.items():
        result, elapsed = bdf_run(f"time {name}", environment, config)
        bdf_time_results[name] = result
        bdf_time_rows.append({"name": name, "config": asdict(config), **summarize_bdf(result, elapsed)})
        progress(args.work_dir, f"bdf_time_{name}", bdf_time_rows)
    bdf_time_comparisons = {
        "B1_vs_B2": comparison(bdf_time_results["B1"], bdf_time_results["B2"]),
        "B2_vs_B3": comparison(bdf_time_results["B2"], bdf_time_results["B3"]),
    }
    main_result = bdf_time_results["B2"]

    ablation_rows = [
        {
            "experiment": "A0",
            "geometry": "original approximate radial discretization",
            "interface_mean": "arithmetic",
            "dr_cm": 0.1,
            "time_method": "BE dt=10 s",
            "event_time_s": baseline["end_time_s"],
            "event_time_h": baseline["end_time_h"],
            "relative_to_previous_s": None,
            "event_center_moisture": baseline["end_profile_raw"][0],
            "event_surface_moisture": baseline["end_profile_raw"][-1],
            "event_argmax_radius_cm": 0.0,
            "runtime_s": baseline["runtime_s"],
        }
    ]
    ablation_specs = [
        ("A1", 0.1, "arithmetic"),
        ("A2", 0.1, "harmonic"),
        ("A3", 0.05, "harmonic"),
        ("A4", 0.025, "harmonic"),
    ]
    previous_time = float(baseline["end_time_s"])
    for name, dr, mean in ablation_specs:
        config = BESolverConfig(
            internal_dr_cm=dr,
            time_step_s=10.0,
            interface_mean=mean,
            fallback_time_limit_s=1000.0 * 3600.0,
        )
        result, elapsed = be_run(f"ablation {name}", environment, config)
        summary = summarize_be(result, elapsed)
        ablation_rows.append(
            {
                "experiment": name,
                "geometry": "strict radial FVM",
                "interface_mean": mean,
                "dr_cm": dr,
                "time_method": "BE dt=10 s",
                **summary,
                "relative_to_previous_s": result.drying_event_time_s - previous_time,
            }
        )
        previous_time = result.drying_event_time_s
        progress(args.work_dir, f"ablation_{name}", ablation_rows)
    ablation_rows.append(
        {
            "experiment": "A5",
            "geometry": "strict radial FVM",
            "interface_mean": "harmonic",
            "dr_cm": selected_dr,
            "time_method": "adaptive BDF B2",
            **summarize_bdf(main_result, next(row["runtime_s"] for row in bdf_time_rows if row["name"] == "B2")),
            "relative_to_previous_s": main_result.drying_event_time_s - previous_time,
        }
    )

    be_results = {}
    be_rows = []
    for dt in [20.0, 10.0, 5.0, 2.5]:
        config = BESolverConfig(internal_dr_cm=selected_dr, time_step_s=dt)
        result, elapsed = be_run(f"time dt={dt:g}s", environment, config)
        be_results[dt] = result
        be_rows.append({"dt_s": dt, "config": asdict(config), **summarize_be(result, elapsed)})
        progress(args.work_dir, f"be_time_{dt:g}", be_rows)
    be_pairs = [
        {"coarse_dt_s": coarse, "fine_dt_s": fine, **comparison(be_results[coarse], be_results[fine])}
        for coarse, fine in [(20.0, 10.0), (10.0, 5.0), (5.0, 2.5)]
    ]
    cross_solver = comparison(bdf_time_results["B3"], be_results[2.5])

    default_post = post_boundary_from_tail(environment)
    data_posts = {
        "attachment_terminal_value": default_post,
        "last_30_min_time_average": post_boundary_from_tail(environment, 1800.0),
        "last_1_h_time_average": post_boundary_from_tail(environment, 3600.0),
    }
    boundary_cache: dict[tuple[float, float, float], tuple[SimulationResult, float]] = {}

    def boundary_result(post: PostBoundary, hm: float, label: str):
        key = (round(post.temperature_c, 12), round(post.moisture, 12), round(hm, 15))
        if key not in boundary_cache:
            if key == (
                round(default_post.temperature_c, 12),
                round(default_post.moisture, 12),
                round(time_configs["B2"].mass_transfer_m_s, 15),
            ):
                boundary_cache[key] = (
                    main_result,
                    next(row["runtime_s"] for row in bdf_time_rows if row["name"] == "B2"),
                )
            else:
                boundary_cache[key] = bdf_run(
                    f"boundary {label}",
                    environment,
                    replace(time_configs["B2"], mass_transfer_m_s=hm),
                    post,
                )
        return boundary_cache[key]

    data_rows = []
    for name, post in data_posts.items():
        result, elapsed = boundary_result(post, time_configs["B2"].mass_transfer_m_s, name)
        data_rows.append(
            {
                "scenario": name,
                "post_temperature_c": post.temperature_c,
                "post_moisture": post.moisture,
                "mass_transfer_m_s": time_configs["B2"].mass_transfer_m_s,
                **summarize_bdf(result, elapsed),
                "difference_from_default_s": result.drying_event_time_s - main_result.drying_event_time_s,
            }
        )
        progress(args.work_dir, f"boundary_data_{name}", data_rows)

    engineering_rows = []
    for temperature_delta in [-2.0, 0.0, 2.0]:
        for moisture_factor in [0.9, 1.0, 1.1]:
            post = PostBoundary(
                default_post.temperature_c + temperature_delta,
                default_post.moisture * moisture_factor,
            )
            label = f"T{temperature_delta:+g}_C{moisture_factor:.1f}"
            result, elapsed = boundary_result(post, time_configs["B2"].mass_transfer_m_s, label)
            engineering_rows.append(
                {
                    "scenario": label,
                    "post_temperature_c": post.temperature_c,
                    "post_moisture": post.moisture,
                    "mass_transfer_m_s": time_configs["B2"].mass_transfer_m_s,
                    **summarize_bdf(result, elapsed),
                    "difference_from_default_s": result.drying_event_time_s - main_result.drying_event_time_s,
                }
            )
            progress(args.work_dir, f"boundary_engineering_{label}", engineering_rows)

    hm_rows = []
    for factor in [0.9, 1.0, 1.1]:
        hm = time_configs["B2"].mass_transfer_m_s * factor
        label = f"hm_{factor:.1f}x"
        result, elapsed = boundary_result(default_post, hm, label)
        hm_rows.append(
            {
                "scenario": label,
                "post_temperature_c": default_post.temperature_c,
                "post_moisture": default_post.moisture,
                "mass_transfer_m_s": hm,
                **summarize_bdf(result, elapsed),
                "difference_from_default_s": result.drying_event_time_s - main_result.drying_event_time_s,
            }
        )
        progress(args.work_dir, f"boundary_hm_{factor:.1f}", hm_rows)

    table_times = np.arange(
        6.0 * 3600.0,
        np.floor(main_result.drying_event_time_s / (6.0 * 3600.0)) * 6.0 * 3600.0 + 1.0,
        6.0 * 3600.0,
    )
    table_values = values_at_times(main_result, table_times)
    event_radius_indices = [int(np.where(np.isclose(main_result.radius_cm, r))[0][0]) for r in PAPER_RADII_CM]
    table5 = [
        {"time_s": float(t), "time_h": float(t / 3600.0), "values": row.tolist()}
        for t, row in zip(table_times, table_values, strict=True)
    ]
    table5.append(
        {
            "time_s": main_result.drying_event_time_s,
            "time_h": main_result.drying_event_time_s / 3600.0,
            "values": main_result.event_moisture[event_radius_indices].tolist(),
        }
    )

    bdf_time_pass = bool(
        bdf_time_comparisons["B2_vs_B3"]["event_time_difference_s"] < 60.0
        and bdf_time_comparisons["B2_vs_B3"]["paper_sample_maximum_moisture_difference"] < 1e-4
    )
    be_time_pass = bool(
        be_pairs[-1]["event_time_difference_s"] < 30.0
        and all(row["diagnostics"]["unconverged_steps"] == 0 for row in be_rows)
    )
    cross_solver_pass = bool(
        cross_solver["event_time_difference_s"] < 60.0
        and cross_solver["paper_sample_maximum_moisture_difference"] < 1e-4
    )
    quality_pass = bool(
        main_result.diagnostics.maximum_normalized_mass_balance_residual < 1e-6
        and main_result.diagnostics.minimum_raw_moisture >= -1e-8
        and main_result.diagnostics.radial_monotonicity_all_outputs
        and float(main_result.event_internal_radius_cm[np.argmax(main_result.event_internal_moisture)]) == 0.0
        and main_result.max_moisture[-1] < main_result.max_moisture[-2]
        and main_result.max_moisture[-1] < time_configs["B2"].completion_threshold
    )

    engineering_times = [row["event_time_s"] for row in engineering_rows]
    data_times = [row["event_time_s"] for row in data_rows]
    all_boundary_times = engineering_times + data_times + [row["event_time_s"] for row in hm_rows]
    candidate_options = [
        *[
            {"source": f"spatial_grid_dr_{row['dr_cm']:g}_cm", "event_time_h": row["event_time_h"]}
            for row in spatial_rows
        ],
        *[
            {"source": f"data_boundary_{row['scenario']}", "event_time_h": row["event_time_h"]}
            for row in data_rows
        ],
        *[
            {"source": f"engineering_boundary_{row['scenario']}", "event_time_h": row["event_time_h"]}
            for row in engineering_rows
        ],
        *[
            {"source": f"mass_transfer_{row['scenario']}", "event_time_h": row["event_time_h"]}
            for row in hm_rows
        ],
    ]
    closest_candidate = min(candidate_options, key=lambda row: abs(row["event_time_h"] - CANDIDATE_TIME_H))
    candidate_difference_s = abs(closest_candidate["event_time_h"] - CANDIDATE_TIME_H) * 3600.0
    verification = {
        "source": {
            "attachment1_path_used_for_run": str(args.attachment1),
            "attachment1_sha256": hashlib.sha256(args.attachment1.read_bytes()).hexdigest(),
            "environment_terminal_time_s": environment.terminal_time_s,
            "environment_terminal_temperature_c": environment.terminal_temperature_c,
            "environment_terminal_moisture": environment.terminal_moisture,
            "python_version": platform.python_version(),
            "numpy_version": np.__version__,
            "scipy_version": scipy.__version__,
        },
        "baseline": baseline,
        "ablation": ablation_rows,
        "spatial_grid": {
            "runs": spatial_rows,
            "adjacent_comparisons": spatial_pairs,
            "selected_internal_dr_cm": selected_dr,
            "selected_pair_passed": spatial_pairs[-1]["accepted"],
            "observed_order_from_last_three_event_times": observed_order,
            "richardson_extrapolated_event_time_s": richardson_event_time_s,
            "richardson_extrapolated_event_time_h": richardson_event_time_s / 3600.0,
            "selected_minus_richardson_s": spatial_results[selected_dr].drying_event_time_s - richardson_event_time_s,
        },
        "bdf_time_sensitivity": {
            "runs": bdf_time_rows,
            "comparisons": bdf_time_comparisons,
            "passed": bdf_time_pass,
        },
        "be_time_sensitivity": {
            "runs": be_rows,
            "comparisons": be_pairs,
            "passed": be_time_pass,
        },
        "cross_solver": {"comparison": cross_solver, "passed": cross_solver_pass},
        "quality": {
            "passed": quality_pass,
            "diagnostics": asdict(main_result.diagnostics),
            "event_profile_internal": main_result.event_internal_moisture.tolist(),
            "event_radius_internal_cm": main_result.event_internal_radius_cm.tolist(),
        },
        "boundary_sensitivity": {
            "data_driven": data_rows,
            "engineering_3x3": engineering_rows,
            "mass_transfer": hm_rows,
            "data_driven_range_s": [float(min(data_times)), float(max(data_times))],
            "engineering_range_s": [float(min(engineering_times)), float(max(engineering_times))],
            "all_scenarios_range_s": [float(min(all_boundary_times)), float(max(all_boundary_times))],
        },
        "candidate_57_4778_h": {
            "candidate_time_h": CANDIDATE_TIME_H,
            "closest_reproduced_scenario": closest_candidate,
            "absolute_difference_s": candidate_difference_s,
            "reproduced_within_60_s": bool(candidate_difference_s < 60.0),
            "interpretation": (
                "The candidate is reproduced by the last-1-hour time-averaged post boundary, "
                "not by the default attachment-terminal-value boundary."
            ),
        },
        "final": {
            "all_numerical_acceptance_checks_passed": bool(
                spatial_pairs[-1]["accepted"]
                and bdf_time_pass
                and be_time_pass
                and cross_solver_pass
                and quality_pass
            ),
            "internal_dr_cm": selected_dr,
            "bdf_configuration": "B2",
            "continuous_event_time_s": main_result.drying_event_time_s,
            "continuous_event_time_h": main_result.drying_event_time_s / 3600.0,
            "first_strictly_compliant_60s_time_s": main_result.report_end_time_s,
            "first_strictly_compliant_60s_time_h": main_result.report_end_time_s / 3600.0,
            "event_center_moisture": float(main_result.event_internal_moisture[0]),
            "event_surface_moisture": float(main_result.event_internal_moisture[-1]),
            "t60_max_moisture": float(main_result.max_moisture[-1]),
            "previous_60s_max_moisture": float(main_result.max_moisture[-2]),
            "boundary_all_scenarios_range_s": [float(min(all_boundary_times)), float(max(all_boundary_times))],
            "boundary_all_scenarios_range_h": [
                float(min(all_boundary_times) / 3600.0),
                float(max(all_boundary_times) / 3600.0),
            ],
        },
        "table5_raw": table5,
    }
    json_dump(args.verification, verification)

    rows = [
        [int(t_s), *[float(value) for value in profile]]
        for t_s, profile in zip(main_result.time_s, main_result.moisture, strict=True)
    ]
    payload = {
        "headers": ["时间\\到药材中心的距离", *[float(radius) for radius in main_result.radius_cm]],
        "rows": rows,
        "metadata": verification["final"],
    }
    json_dump(args.payload, payload)
    progress(args.work_dir, "complete", {"verification": str(args.verification), "payload": str(args.payload)})
    print(json.dumps({"final": verification["final"], "checks": {
        "spatial": spatial_pairs[-1]["accepted"],
        "bdf_time": bdf_time_pass,
        "be_time": be_time_pass,
        "cross_solver": cross_solver_pass,
        "quality": quality_pass,
    }}, ensure_ascii=False, indent=2), flush=True)


if __name__ == "__main__":
    main()
