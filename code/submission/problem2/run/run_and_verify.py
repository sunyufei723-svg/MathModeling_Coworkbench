from __future__ import annotations

import argparse
import json
import os
import sys
from dataclasses import asdict, replace
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "core"))

from solver import EnvironmentSeries, SimulationResult, SolverConfig, solve_problem2


PROJECT_ROOT = Path(__file__).resolve().parents[4]
ORIGINAL_RESULT = PROJECT_ROOT / "results" / "problem2" / "result2.xlsx"
SAMPLE_SECONDS = np.array([1800, 3600, 5400, 7200, 9000, 10800], dtype=float)
SAMPLE_RADIUS_CM = np.array([0.0, 0.5, 1.0, 1.5, 2.0], dtype=float)


def resolve_attachment1(explicit_path: Path | None = None) -> Path:
    if explicit_path is not None:
        candidates = [explicit_path]
    else:
        candidates = []
        source_dir = os.environ.get("CUMCM_A_PROBLEM_DIR")
        if source_dir:
            candidates.append(Path(source_dir) / "附件" / "附件1.xlsx")
        candidates.extend(
            [
                PROJECT_ROOT / "附件" / "附件1.xlsx",
                PROJECT_ROOT / "files" / "raw" / "CUMCM2026Problems" / "A题" / "附件" / "附件1.xlsx",
            ]
        )
    for candidate in candidates:
        if candidate.exists():
            return candidate
    searched = "\n".join(str(path) for path in candidates)
    raise FileNotFoundError(
        "未找到附件1.xlsx。请使用 --attachment1 指定路径，或设置 CUMCM_A_PROBLEM_DIR。\n"
        f"已搜索：\n{searched}"
    )


def load_environment(path: Path) -> EnvironmentSeries:
    frame = pd.read_excel(path)
    required = ["时间", "温度", "水分浓度"]
    missing = [name for name in required if name not in frame.columns]
    if missing:
        raise ValueError(f"附件1缺少列：{missing}")
    return EnvironmentSeries(
        time_s=frame["时间"].to_numpy(dtype=float),
        temperature_c=frame["温度"].to_numpy(dtype=float),
        moisture=frame["水分浓度"].to_numpy(dtype=float),
    )


def selected_values(result: SimulationResult, values: np.ndarray) -> np.ndarray:
    time_indices = [int(np.where(np.isclose(result.time_s, value))[0][0]) for value in SAMPLE_SECONDS]
    radius_indices = [int(np.where(np.isclose(result.radius_cm, value))[0][0]) for value in SAMPLE_RADIUS_CM]
    return values[np.ix_(time_indices, radius_indices)]


def difference_summary(
    left: np.ndarray,
    right: np.ndarray,
    times: np.ndarray,
    radii: np.ndarray,
) -> dict[str, object]:
    difference = left - right
    absolute = np.abs(difference)
    location = np.unravel_index(int(np.argmax(absolute)), absolute.shape)
    return {
        "maximum_absolute_difference": float(absolute[location]),
        "signed_difference_at_maximum": float(difference[location]),
        "time_s_at_maximum": float(times[location[0]]),
        "radius_cm_at_maximum": float(radii[location[1]]),
        "mean_absolute_difference": float(absolute.mean()),
        "four_decimal_cells_equal": int(np.count_nonzero(np.round(left, 4) == np.round(right, 4))),
        "cell_count": int(left.size),
    }


def result_rows(result: SimulationResult, values: np.ndarray) -> list[list[float | int]]:
    rounded = np.round(values[1:, :], 4)
    return [
        [int(time_s), *[float(value) for value in row]]
        for time_s, row in zip(result.time_s[1:], rounded, strict=True)
    ]


def selected_table_payload(result: SimulationResult, values: np.ndarray) -> list[dict[str, object]]:
    selected = selected_values(result, values)
    rows = []
    for row_index, time_s in enumerate(SAMPLE_SECONDS):
        rows.append(
            {
                "time_h": float(time_s / 3600.0),
                "values": [float(value) for value in selected[row_index]],
            }
        )
    return rows


def load_original_result(path: Path) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    temperature = pd.read_excel(path, sheet_name="温度")
    moisture = pd.read_excel(path, sheet_name="水分浓度")
    time_s = temperature.iloc[:, 0].to_numpy(dtype=float)
    if not np.array_equal(time_s, moisture.iloc[:, 0].to_numpy(dtype=float)):
        raise ValueError("原问题二温度/水分工作表的时间列不一致")
    return (
        time_s,
        temperature.iloc[:, 1:].to_numpy(dtype=float),
        moisture.iloc[:, 1:].to_numpy(dtype=float),
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="运行问题二严格 FVM+BDF 解并完成数值复核")
    parser.add_argument("--attachment1", type=Path, default=None)
    parser.add_argument("--payload", type=Path, required=True, help="供 Artifact Tool 导出 Excel 的 JSON")
    parser.add_argument("--verification", type=Path, required=True, help="数值复核 JSON")
    args = parser.parse_args()

    attachment = resolve_attachment1(args.attachment1)
    environment = load_environment(attachment)
    main_config = SolverConfig(internal_dr_cm=0.025)
    fine_config = replace(main_config, internal_dr_cm=0.0125)
    strict_time_config = replace(
        main_config,
        relative_tolerance=1e-9,
        temperature_absolute_tolerance=1e-10,
        moisture_absolute_tolerance=1e-11,
        max_time_step_s=2.0,
    )
    early_ultrafine_config = replace(
        main_config,
        internal_dr_cm=0.00625,
        duration_s=60,
        relative_tolerance=1e-9,
        temperature_absolute_tolerance=1e-10,
        moisture_absolute_tolerance=1e-11,
        max_time_step_s=0.5,
    )

    print("running main grid dr=0.025 cm", flush=True)
    main_result = solve_problem2(environment, main_config)
    print("running fine grid dr=0.0125 cm", flush=True)
    fine_result = solve_problem2(environment, fine_config)
    print("running stricter BDF time settings", flush=True)
    strict_time_result = solve_problem2(environment, strict_time_config)
    print("running early-time ultrafine check dr=0.00625 cm for 60 s", flush=True)
    early_ultrafine_result = solve_problem2(environment, early_ultrafine_config)

    main_temperature_selected = selected_values(main_result, main_result.temperature_c)
    main_moisture_selected = selected_values(main_result, main_result.moisture)
    fine_temperature_selected = selected_values(fine_result, fine_result.temperature_c)
    fine_moisture_selected = selected_values(fine_result, fine_result.moisture)
    strict_temperature_selected = selected_values(strict_time_result, strict_time_result.temperature_c)
    strict_moisture_selected = selected_values(strict_time_result, strict_time_result.moisture)

    old_time_s, old_temperature, old_moisture = load_original_result(ORIGINAL_RESULT)
    if not np.array_equal(old_time_s, main_result.time_s[1:]):
        raise ValueError("原问题二结果与新方案的导出时间网格不一致")
    old_temperature_selected = old_temperature[
        np.ix_((SAMPLE_SECONDS.astype(int) - 1), (SAMPLE_RADIUS_CM / 0.1).astype(int))
    ]
    old_moisture_selected = old_moisture[
        np.ix_((SAMPLE_SECONDS.astype(int) - 1), (SAMPLE_RADIUS_CM / 0.1).astype(int))
    ]

    verification = {
        "source_attachment": str(attachment),
        "main_config": asdict(main_config),
        "fine_config": asdict(fine_config),
        "strict_time_config": asdict(strict_time_config),
        "diagnostics": {
            "main": asdict(main_result.diagnostics),
            "fine": asdict(fine_result.diagnostics),
            "strict_time": asdict(strict_time_result.diagnostics),
            "early_ultrafine": asdict(early_ultrafine_result.diagnostics),
        },
        "spatial_refinement_at_paper_samples": {
            "temperature_c": difference_summary(
                main_temperature_selected,
                fine_temperature_selected,
                SAMPLE_SECONDS,
                SAMPLE_RADIUS_CM,
            ),
            "moisture": difference_summary(
                main_moisture_selected,
                fine_moisture_selected,
                SAMPLE_SECONDS,
                SAMPLE_RADIUS_CM,
            ),
        },
        "spatial_refinement_on_full_output_grid": {
            "temperature_c": difference_summary(
                main_result.temperature_c,
                fine_result.temperature_c,
                main_result.time_s,
                main_result.radius_cm,
            ),
            "moisture": difference_summary(
                main_result.moisture,
                fine_result.moisture,
                main_result.time_s,
                main_result.radius_cm,
            ),
        },
        "time_solver_sensitivity_at_paper_samples": {
            "temperature_c": difference_summary(
                main_temperature_selected,
                strict_temperature_selected,
                SAMPLE_SECONDS,
                SAMPLE_RADIUS_CM,
            ),
            "moisture": difference_summary(
                main_moisture_selected,
                strict_moisture_selected,
                SAMPLE_SECONDS,
                SAMPLE_RADIUS_CM,
            ),
        },
        "early_time_spatial_check_0_to_60_s": {
            "comparison": "dr=0.0125 cm versus dr=0.00625 cm",
            "temperature_c": difference_summary(
                fine_result.temperature_c[:61],
                early_ultrafine_result.temperature_c,
                fine_result.time_s[:61],
                fine_result.radius_cm,
            ),
            "moisture": difference_summary(
                fine_result.moisture[:61],
                early_ultrafine_result.moisture,
                fine_result.time_s[:61],
                fine_result.radius_cm,
            ),
        },
        "old_vs_new_at_paper_samples": {
            "temperature_c": difference_summary(
                main_temperature_selected,
                old_temperature_selected,
                SAMPLE_SECONDS,
                SAMPLE_RADIUS_CM,
            ),
            "moisture": difference_summary(
                main_moisture_selected,
                old_moisture_selected,
                SAMPLE_SECONDS,
                SAMPLE_RADIUS_CM,
            ),
        },
        "old_vs_new_on_full_output_grid": {
            "temperature_c": difference_summary(
                main_result.temperature_c[1:],
                old_temperature,
                old_time_s,
                main_result.radius_cm,
            ),
            "moisture": difference_summary(
                main_result.moisture[1:],
                old_moisture,
                old_time_s,
                main_result.radius_cm,
            ),
        },
        "claimed_previous_refinement_difference": {
            "temperature_c": 3.97e-5,
            "moisture": 4.67e-5,
        },
        "selected_tables": {
            "temperature_c": selected_table_payload(main_result, main_result.temperature_c),
            "moisture": selected_table_payload(main_result, main_result.moisture),
            "old_temperature_c": [row.tolist() for row in old_temperature_selected],
            "old_moisture": [row.tolist() for row in old_moisture_selected],
        },
    }
    payload = {
        "metadata": {
            "method": "conservative radial FVM + coupled adaptive BDF",
            "internal_dr_cm": main_config.internal_dr_cm,
            "output_dr_cm": main_config.output_dr_cm,
            "output_dt_s": main_config.output_dt_s,
            "duration_s": main_config.duration_s,
        },
        "headers": ["时间\\到药材中心的距离", *[f"{value:.1f}" for value in main_result.radius_cm]],
        "temperature_rows": result_rows(main_result, main_result.temperature_c),
        "moisture_rows": result_rows(main_result, main_result.moisture),
    }

    args.payload.parent.mkdir(parents=True, exist_ok=True)
    args.verification.parent.mkdir(parents=True, exist_ok=True)
    args.payload.write_text(json.dumps(payload, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    args.verification.write_text(json.dumps(verification, ensure_ascii=False, indent=2), encoding="utf-8")

    compact = {
        "payload": str(args.payload),
        "verification": str(args.verification),
        "diagnostics": verification["diagnostics"],
        "spatial_samples": verification["spatial_refinement_at_paper_samples"],
        "time_samples": verification["time_solver_sensitivity_at_paper_samples"],
        "old_vs_new_samples": verification["old_vs_new_at_paper_samples"],
        "selected_tables": verification["selected_tables"],
    }
    print(json.dumps(compact, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
