from __future__ import annotations

import argparse
import hashlib
import json
import platform
import sys
import time
from itertools import product
from pathlib import Path

import numpy as np
import scipy

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "business" / "sensitivity"))
try:
    from .evaluator import BASELINE_EVENT_TIME_S, ModelEvaluator
    from .morris import analyse_morris, generate_morris_design
    from .parameters import PARAMETER_SPECS, default_unit_point, parameter_metadata, parameter_names
    from .pce import design_matrix, fit_pce, latin_hypercube, validation_metrics, validation_passed
    from .radau_crosscheck import compare_integrators
    from .sobol import analytical_sobol, bootstrap_sobol, merge_sobol_checks, saltelli_crosscheck
except ImportError:
    from evaluator import BASELINE_EVENT_TIME_S, ModelEvaluator  # type: ignore
    from morris import analyse_morris, generate_morris_design  # type: ignore
    from parameters import PARAMETER_SPECS, default_unit_point, parameter_metadata, parameter_names  # type: ignore
    from pce import design_matrix, fit_pce, latin_hypercube, validation_metrics, validation_passed  # type: ignore
    from radau_crosscheck import compare_integrators  # type: ignore
    from sobol import analytical_sobol, bootstrap_sobol, merge_sobol_checks, saltelli_crosscheck  # type: ignore


def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False), encoding="utf-8")


def file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def embed_selected(points: np.ndarray, selected_indices: list[int]) -> np.ndarray:
    full = np.tile(default_unit_point(), (len(points), 1))
    full[:, selected_indices] = points
    return full


def event_outputs(records: list[dict[str, object]]) -> np.ndarray:
    return np.asarray([float(record["continuous_event_time_h"]) for record in records], dtype=float)


def unique_rows(points: list[np.ndarray]) -> list[np.ndarray]:
    unique: dict[tuple[float, ...], np.ndarray] = {}
    for point in points:
        key = tuple(round(float(value), 12) for value in point)
        unique[key] = np.asarray(point, dtype=float)
    return list(unique.values())


def recorded_solver_cost(record_groups: list[list[dict[str, object]]]) -> dict[str, float | int]:
    """Summarise the unique PDE solves represented by the final data products.

    This is intentionally distinct from the wall time of a resumed, cache-backed
    pipeline run.  A physical sample is identified by its grid, integrator and
    full nine-parameter unit point.
    """
    unique: dict[tuple[object, ...], dict[str, object]] = {}
    for records in record_groups:
        for record in records:
            key = (
                int(record["node_count"]),
                str(record["integration_method"]),
                *tuple(round(float(value), 12) for value in record["unit_point"]),
            )
            unique[key] = record
    return {
        "unique_pde_evaluation_count_in_final_dataset": len(unique),
        "sum_recorded_solver_runtime_s": float(
            sum(float(record["runtime_s"]) for record in unique.values())
        ),
    }


def markdown_table(headers: list[str], rows: list[list[str]]) -> str:
    return "\n".join(
        [
            "| " + " | ".join(headers) + " |",
            "|" + "|".join("---" for _ in headers) + "|",
            *["| " + " | ".join(row) + " |" for row in rows],
        ]
    )


def write_report(
    path: Path,
    morris: dict[str, object],
    pce: dict[str, object],
    sobol: dict[str, object],
    high_fidelity: dict[str, object],
    radau: dict[str, object],
) -> None:
    morris_rows = [
        [
            str(index),
            str(row["parameter"]),
            f"{float(row['mu_h']):.6f}",
            f"{float(row['mu_star_h']):.6f}",
            f"{float(row['sigma_h']):.6f}",
        ]
        for index, row in enumerate(morris["rows"], start=1)
    ]
    sobol_rows = [
        [
            str(row["parameter"]),
            f"{float(row['first_order']):.5f}",
            f"{float(row['total_order']):.5f}",
            "[" + ", ".join(f"{float(value):.6f}" for value in row["first_order_95_interval"]) + "]",
            "[" + ", ".join(f"{float(value):.6f}" for value in row["total_order_95_interval"]) + "]",
        ]
        for row in sobol["analytical"]["rows"]
    ]
    hf_rows = [
        [
            str(row["scenario"]),
            f"{float(row['pce_prediction_h']):.6f}",
            f"{float(row['pde_event_time_h']):.6f}",
            f"{float(row['absolute_error_h']):.6f}",
        ]
        for row in high_fidelity["rows"]
    ]
    radau_rows = [
        [
            str(row["scenario"]),
            f"{float(row['bdf_event_time_h']):.6f}",
            f"{float(row['radau_event_time_h']):.6f}",
            f"{float(row['absolute_difference_s']):.4f}",
            f"{float(row['representative_profile_maximum_moisture_difference']):.3e}",
        ]
        for row in radau["rows"]
    ]
    interaction_rows = [
        [
            str(row["parameter_left"]),
            str(row["parameter_right"]),
            f"{float(row['second_order']):.6f}",
        ]
        for row in sobol["analytical"]["interactions"][:3]
    ]
    distribution = pce["conditional_distribution_summary"]
    path.write_text(
        "\n".join(
            [
                "# 问题四全局敏感性、PCE/Sobol与Radau验证报告",
                "",
                "本报告只研究题设直接给定的物质坐标问题四主模型。干物质质量闭合替代模型是离散的模型形式层，不混入连续Sobol参数空间。所有参数均按声明的独立均匀工程扰动分布处理，因此结论不是由观测数据估计的统计置信区间。",
                "",
                "## 1. Morris筛选",
                "",
                f"采用 {morris['trajectory_count']} 条轨迹、{morris['model_evaluation_count']} 次N401高保真PDE计算。mu_star衡量筛选影响强度，不能解释成方差贡献率。",
                "",
                markdown_table(["排名", "参数", "mu/h", "mu_star/h", "sigma/h"], morris_rows),
                "",
                "进入PCE/Sobol的参数：" + ", ".join(morris["selected_parameters"]),
                "",
                "## 2. PCE代理及独立验证",
                "",
                f"最终采用 {pce['selected_degree']} 阶Legendre PCE；训练样本 {pce['training_sample_count']} 个，独立验证样本 {pce['validation_sample_count']} 个。",
                "",
                f"独立验证：Q²={pce['metrics']['q_squared_independent']:.9f}，RMSE={pce['metrics']['rmse_h']:.6f} h，最大绝对误差={pce['metrics']['maximum_absolute_error_h']:.6f} h，NRMSE={pce['metrics']['normalized_rmse_by_range']:.6f}。验收：{'通过' if pce['passed'] else '未通过'}。",
                "",
                f"在保留的5个变量服从所声明独立均匀分布、其余4个变量固定于基准值的条件下，PCE抽样均值={distribution['mean_h']:.4f} h，标准差={distribution['standard_deviation_h']:.4f} h，P5={distribution['p05_h']:.4f} h，中位数={distribution['median_h']:.4f} h，P95={distribution['p95_h']:.4f} h。该范围是工程扰动假设下的条件分布，不是统计置信区间。",
                "",
                "## 3. Sobol方差分解",
                "",
                "以下Sobol指数由通过独立PDE验证的正交PCE系数计算，并用廉价Saltelli抽样交叉检查。它是Morris筛选后5参数的条件Sobol分析；未入选的4个参数固定在基准值。尤其应注意，活化温度参数的主导程度依赖于预先声明的±5%工程范围。",
                "",
                markdown_table(["参数", "一阶S_i", "总效应S_Ti", "一阶95%区间", "总效应95%区间"], sobol_rows),
                "",
                f"一阶指数和={sobol['analytical']['sum_first_order']:.6f}；PCE解析值与Saltelli数值值的最大差={sobol['crosscheck']['maximum_absolute_difference']:.6f}，验收：{'通过' if sobol['crosscheck']['passed'] else '未通过'}。",
                "",
                "最大的二阶交互项为：",
                "",
                markdown_table(["参数1", "参数2", "二阶指数"], interaction_rows),
                "",
                "表中95%区间仅量化PCE拟合残差经重抽样后造成的代理系数不确定性；它们不是参数分布、观测误差或模型形式的统计置信区间。",
                "",
                "## 4. N3201高保真抽查",
                "",
                markdown_table(["情景", "PCE/h", "PDE/h", "绝对误差/h"], hf_rows),
                "",
                f"默认参数化求解器相对既有基准182968.225162 s的差={high_fidelity['baseline_absolute_difference_s']:.6f} s；总体验收：{'通过' if high_fidelity['passed'] else '未通过'}。",
                "",
                "## 5. Radau IIA交叉验证",
                "",
                markdown_table(["情景", "BDF/h", "Radau/h", "差异/s", "代表剖面最大水分差"], radau_rows),
                "",
                f"Radau只用于默认、快速样本和慢速样本三个情景，不参与批量UQ。事件时间差小于30 s且代表时刻全剖面最大水分差小于1e-4的联合验收：{'通过' if radau['passed'] else '未通过'}。",
                "",
                "## 6. 结论边界",
                "",
                "Morris用于筛选而非方差归因；Sobol指数是在给定独立均匀工程扰动范围下、基于经高保真PDE验证的PCE代理得到。结果不替换问题四主答案50.8245 h，也不包含收缩/密度闭合替代模型的离散模型形式不确定性。",
                "",
            ]
        ),
        encoding="utf-8",
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="运行问题四Morris-PCE-Sobol-Radau完整流水线")
    parser.add_argument("--attachment1", required=True, type=Path)
    parser.add_argument("--attachment2", required=True, type=Path)
    parser.add_argument("--work-dir", required=True, type=Path)
    parser.add_argument("--results-dir", required=True, type=Path)
    parser.add_argument("--workers", type=int, default=1)
    parser.add_argument("--morris-trajectories-per-seed", type=int, default=10)
    parser.add_argument("--pce-training", type=int, default=160)
    parser.add_argument("--pce-validation", type=int, default=40)
    args = parser.parse_args()
    args.work_dir.mkdir(parents=True, exist_ok=True)
    args.results_dir.mkdir(parents=True, exist_ok=True)
    evaluator = ModelEvaluator(
        args.attachment1,
        args.attachment2,
        args.work_dir / "evaluation_cache.json",
        workers=args.workers,
    )
    started_all = time.perf_counter()

    parameter_payload = {
        "target": "problem4 continuous drying event time t_star",
        "distributions": "independent uniform engineering perturbations",
        "not_statistical_confidence_interval": True,
        "model_form_exclusion": "dry-mass-closure alternative remains a separate discrete layer",
        "parameters": parameter_metadata(),
        "attachments": {
            "attachment1_sha256": file_sha256(args.attachment1),
            "attachment2_sha256": file_sha256(args.attachment2),
        },
        "software": {
            "python": platform.python_version(),
            "numpy": np.__version__,
            "scipy": scipy.__version__,
        },
    }
    write_json(args.results_dir / "parameter_ranges.json", parameter_payload)

    print("STAGE Morris", flush=True)
    design = generate_morris_design(
        len(PARAMETER_SPECS),
        trajectories_per_seed=args.morris_trajectories_per_seed,
    )
    morris_records = evaluator.evaluate_many(design.points, node_count=401, integration_method="BDF")
    morris = analyse_morris(design, event_outputs(morris_records), parameter_names())
    morris["design_unit_points"] = design.points.tolist()
    morris["event_time_h"] = event_outputs(morris_records).tolist()
    morris["all_quality_checks_passed"] = all(bool(row["quality_checks_passed"]) for row in morris_records)
    write_json(args.results_dir / "morris_results.json", morris)

    selected_names = tuple(str(name) for name in morris["selected_parameters"])
    name_to_index = {name: index for index, name in enumerate(parameter_names())}
    selected_indices = [name_to_index[name] for name in selected_names]

    print("STAGE PCE training and independent validation", flush=True)
    lhs_train_reduced = latin_hypercube(args.pce_training, len(selected_indices), seed=20260916)
    corner_reduced = np.asarray(
        list(product((0.0, 1.0), repeat=len(selected_indices))),
        dtype=float,
    )
    train_reduced = np.vstack([lhs_train_reduced, corner_reduced])
    validation_reduced = latin_hypercube(args.pce_validation, len(selected_indices), seed=20260917)
    train_full = embed_selected(train_reduced, selected_indices)
    validation_full = embed_selected(validation_reduced, selected_indices)
    train_records = evaluator.evaluate_many(train_full, node_count=801, integration_method="BDF")
    validation_records = evaluator.evaluate_many(validation_full, node_count=801, integration_method="BDF")
    train_outputs = event_outputs(train_records)
    validation_outputs = event_outputs(validation_records)

    degree_results = []
    selected_model = None
    selected_metrics = None
    for degree in (2, 3, 4):
        model = fit_pce(train_reduced, train_outputs, selected_names, degree)
        metrics = validation_metrics(validation_outputs, model.predict(validation_reduced))
        passed = validation_passed(metrics)
        degree_results.append({"degree": degree, "metrics": metrics, "passed": passed})
        if selected_model is None and passed:
            selected_model = model
            selected_metrics = metrics
    if selected_model is None or selected_metrics is None:
        failure = {
            "selected_parameters": list(selected_names),
            "degree_results": degree_results,
            "passed": False,
            "message": "No degree-2 through degree-4 PCE passed independent validation",
        }
        write_json(args.results_dir / "pce_validation.json", failure)
        raise RuntimeError(failure["message"])
    pce_predictions = selected_model.predict(validation_reduced)
    pce_payload = {
        "selected_parameters": list(selected_names),
        "selected_degree": selected_model.degree,
        "training_sample_count": len(train_outputs),
        "latin_hypercube_training_sample_count": len(lhs_train_reduced),
        "corner_enrichment_sample_count": len(corner_reduced),
        "validation_sample_count": len(validation_outputs),
        "degree_results": degree_results,
        "metrics": selected_metrics,
        "passed": True,
        "model": selected_model.as_dict(),
        "design_matrix_condition_number": float(
            np.linalg.cond(design_matrix(train_reduced, selected_model.multi_indices))
        ),
        "training": {
            "reduced_unit_points": train_reduced.tolist(),
            "event_time_h": train_outputs.tolist(),
        },
        "validation": {
            "reduced_unit_points": validation_reduced.tolist(),
            "event_time_h": validation_outputs.tolist(),
            "prediction_h": pce_predictions.tolist(),
            "error_h": (pce_predictions - validation_outputs).tolist(),
        },
    }
    print("STAGE Sobol", flush=True)
    analytical = analytical_sobol(selected_model)
    bootstrap = bootstrap_sobol(
        train_reduced,
        train_outputs,
        selected_names,
        selected_model.degree,
        repetitions=500,
    )
    for row in analytical["rows"]:
        row.update(bootstrap[str(row["parameter"])])
    saltelli = saltelli_crosscheck(selected_model, sample_count=100000)
    crosscheck = merge_sobol_checks(analytical, saltelli)
    sobol_payload = {
        "method": "orthonormal Legendre PCE coefficients with Saltelli surrogate cross-check",
        "distribution_assumption": "independent uniform engineering ranges",
        "conditioning": "five Morris-selected parameters vary; four excluded parameters remain at baseline",
        "not_direct_full_pde_saltelli": True,
        "bootstrap_interval_interpretation": "residual-bootstrap PCE coefficient uncertainty only; not a physical or statistical parameter confidence interval",
        "analytical": analytical,
        "saltelli_surrogate_crosscheck": saltelli,
        "crosscheck": crosscheck,
    }
    write_json(args.results_dir / "sobol_indices.json", sobol_payload)

    print("STAGE N3201 high-fidelity checks", flush=True)
    candidate_reduced = latin_hypercube(100000, len(selected_indices), seed=20260918)
    candidate_predictions = selected_model.predict(candidate_reduced)
    pce_payload["conditional_distribution_summary"] = {
        "sample_count": len(candidate_predictions),
        "conditioning": "selected five parameters vary independently and uniformly; excluded parameters fixed at baseline",
        "mean_h": float(np.mean(candidate_predictions)),
        "standard_deviation_h": float(np.std(candidate_predictions, ddof=1)),
        "p05_h": float(np.quantile(candidate_predictions, 0.05)),
        "median_h": float(np.quantile(candidate_predictions, 0.50)),
        "p95_h": float(np.quantile(candidate_predictions, 0.95)),
        "minimum_sample_h": float(np.min(candidate_predictions)),
        "maximum_sample_h": float(np.max(candidate_predictions)),
    }
    write_json(args.results_dir / "pce_validation.json", pce_payload)
    minimum_reduced = candidate_reduced[int(np.argmin(candidate_predictions))]
    maximum_reduced = candidate_reduced[int(np.argmax(candidate_predictions))]
    validation_errors = np.abs(pce_predictions - validation_outputs)
    worst_validation = np.argsort(validation_errors)[-3:]
    high_points = unique_rows(
        [
            default_unit_point(),
            embed_selected(minimum_reduced[None, :], selected_indices)[0],
            embed_selected(maximum_reduced[None, :], selected_indices)[0],
            *[validation_full[index] for index in worst_validation],
        ]
    )
    high_records = evaluator.evaluate_many(high_points, node_count=3201, integration_method="BDF")
    high_reduced = np.asarray(high_points)[:, selected_indices]
    high_predictions = selected_model.predict(high_reduced)
    high_rows = []
    for index, (point, prediction, record) in enumerate(
        zip(high_points, high_predictions, high_records, strict=True)
    ):
        if np.allclose(point, default_unit_point()):
            scenario = "default"
        elif np.allclose(point[selected_indices], minimum_reduced):
            scenario = "surrogate_fast_sample"
        elif np.allclose(point[selected_indices], maximum_reduced):
            scenario = "surrogate_slow_sample"
        else:
            scenario = f"worst_validation_{index}"
        actual = float(record["continuous_event_time_h"])
        high_rows.append(
            {
                "scenario": scenario,
                "unit_point": point.tolist(),
                "pce_prediction_h": float(prediction),
                "pde_event_time_h": actual,
                "absolute_error_h": abs(float(prediction) - actual),
                "quality_checks_passed": bool(record["quality_checks_passed"]),
            }
        )
    default_record = next(row for point, row in zip(high_points, high_records, strict=True) if np.allclose(point, default_unit_point()))
    baseline_difference = abs(float(default_record["continuous_event_time_s"]) - BASELINE_EVENT_TIME_S)
    high_fidelity = {
        "node_count": 3201,
        "rows": high_rows,
        "baseline_reference_event_time_s": BASELINE_EVENT_TIME_S,
        "baseline_parameterized_event_time_s": float(default_record["continuous_event_time_s"]),
        "baseline_absolute_difference_s": float(baseline_difference),
        "passed": bool(
            baseline_difference < 1.0
            and max(float(row["absolute_error_h"]) for row in high_rows) <= 0.1
            and all(bool(row["quality_checks_passed"]) for row in high_rows)
        ),
    }
    write_json(args.results_dir / "high_fidelity_checks.json", high_fidelity)

    print("STAGE Radau", flush=True)
    default_point = default_unit_point()
    fast_point = embed_selected(minimum_reduced[None, :], selected_indices)[0]
    slow_point = embed_selected(maximum_reduced[None, :], selected_indices)[0]
    radau_points = [default_point, fast_point, slow_point]
    scenario_names = ["default", "surrogate_fast_sample", "surrogate_slow_sample"]
    bdf_records = evaluator.evaluate_many(
        radau_points,
        node_count=1601,
        integration_method="BDF",
        include_profiles=True,
    )
    radau_records = evaluator.evaluate_many(
        radau_points,
        node_count=1601,
        integration_method="Radau",
        include_profiles=True,
    )
    radau_payload = compare_integrators(scenario_names, bdf_records, radau_records)
    write_json(args.results_dir / "radau_comparison.json", radau_payload)

    solver_cost = recorded_solver_cost(
        [
            morris_records,
            train_records,
            validation_records,
            high_records,
            bdf_records,
            radau_records,
        ]
    )
    summary = {
        "morris_passed": bool(morris["all_quality_checks_passed"]),
        "pce_passed": bool(pce_payload["passed"]),
        "sobol_crosscheck_passed": bool(crosscheck["passed"]),
        "high_fidelity_passed": bool(high_fidelity["passed"]),
        "radau_passed": bool(radau_payload["passed"]),
        "all_acceptance_checks_passed": bool(
            morris["all_quality_checks_passed"]
            and pce_payload["passed"]
            and crosscheck["passed"]
            and high_fidelity["passed"]
            and radau_payload["passed"]
        ),
        "final_resume_wall_time_s": float(time.perf_counter() - started_all),
        **solver_cost,
        "main_answer_unchanged_h": BASELINE_EVENT_TIME_S / 3600.0,
    }
    write_json(args.results_dir / "pipeline_summary.json", summary)
    write_report(
        args.results_dir / "sensitivity_report.md",
        morris,
        pce_payload,
        sobol_payload,
        high_fidelity,
        radau_payload,
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2), flush=True)


if __name__ == "__main__":
    main()
