from __future__ import annotations

import argparse
import os
from pathlib import Path

import numpy as np
import pandas as pd

from solver import EnvironmentSeries, SolverConfig, solve_problem3


PROJECT_ROOT = Path(__file__).resolve().parents[2]
OUTPUT_DIR = PROJECT_ROOT / "results" / "problem3"


def resolve_attachment1(project_root: Path = PROJECT_ROOT, explicit_path: Path | None = None) -> Path:
    if explicit_path is not None:
        candidates = [explicit_path]
    else:
        candidates = []
        env_source_dir = os.environ.get("CUMCM_A_PROBLEM_DIR")
        if env_source_dir:
            candidates.append(Path(env_source_dir) / "附件" / "附件1.xlsx")
        candidates.append(project_root / "files" / "raw" / "CUMCM2026Problems" / "A题" / "附件" / "附件1.xlsx")

    for candidate in candidates:
        if candidate.exists():
            return candidate

    searched = "\n".join(str(candidate) for candidate in candidates)
    raise FileNotFoundError(
        "未找到附件1.xlsx。请用 --attachment1 指定文件，或设置 CUMCM_A_PROBLEM_DIR 为 A题目录。\n"
        f"已搜索：\n{searched}"
    )


def load_environment(path: Path) -> EnvironmentSeries:
    frame = pd.read_excel(path)
    return EnvironmentSeries(
        time_s=frame["时间"].to_numpy(dtype=float),
        temperature_c=frame["温度"].to_numpy(dtype=float),
        moisture=frame["水分浓度"].to_numpy(dtype=float),
    )


def moisture_to_frame(time_s: np.ndarray, radius_cm: np.ndarray, moisture: np.ndarray) -> pd.DataFrame:
    frame = pd.DataFrame(moisture, columns=[f"{r:.1f}" for r in radius_cm])
    frame.insert(0, "时间\\到药材中心的距离", time_s.astype(int))
    return frame


def selected_moisture_table(result, interval_h: int = 6) -> pd.DataFrame:
    sample_radius = [0, 0.5, 1.0, 1.5, 2.0]
    sample_seconds = list(range(interval_h * 3600, result.drying_end_time_s + 1, interval_h * 3600))
    if not sample_seconds or sample_seconds[-1] != result.drying_end_time_s:
        sample_seconds.append(result.drying_end_time_s)

    rows = []
    for t_s in sample_seconds:
        source_index = int(np.abs(result.time_s - t_s).argmin())
        row = {"时间/h": f"{t_s / 3600.0:.4f}" if t_s == result.drying_end_time_s else f"{t_s / 3600.0:.0f}"}
        for radius in sample_radius:
            radius_index = int(np.where(np.isclose(result.radius_cm, radius))[0][0])
            row[f"{radius:g} cm"] = f"{float(result.moisture[source_index, radius_index]):.6f}"
        rows.append(row)
    return pd.DataFrame(rows)


def dataframe_to_markdown(frame: pd.DataFrame) -> str:
    headers = [str(column) for column in frame.columns]
    rows = [[str(value) for value in row] for row in frame.to_numpy()]
    lines = [
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join(["---"] * len(headers)) + " |",
    ]
    lines.extend("| " + " | ".join(row) + " |" for row in rows)
    return "\n".join(lines)


def write_outputs(result) -> tuple[Path, Path]:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    workbook_path = OUTPUT_DIR / "result3.xlsx"
    table_path = OUTPUT_DIR / "problem3_tables.md"

    moisture_frame = moisture_to_frame(result.time_s, result.radius_cm, result.moisture)
    with pd.ExcelWriter(workbook_path, engine="openpyxl") as writer:
        moisture_frame.to_excel(writer, sheet_name="水分浓度", index=False)

    table = selected_moisture_table(result)
    text = [
        "# A题第三问论文表格结果",
        "",
        f"烘干结束时间：{result.drying_end_time_s / 3600.0:.4f} h",
        "",
        "## 表5 药材烘干过程的水分浓度",
        "",
        dataframe_to_markdown(table),
        "",
    ]
    table_path.write_text("\n".join(text), encoding="utf-8")
    return workbook_path, table_path


def main() -> None:
    parser = argparse.ArgumentParser(description="求解 A题第三问并生成 result3.xlsx")
    parser.add_argument("--attachment1", type=Path, default=None, help="附件1.xlsx 的路径")
    parser.add_argument("--dt", type=float, default=10.0, help="内部时间步长，单位 s")
    args = parser.parse_args()

    attachment1 = resolve_attachment1(explicit_path=args.attachment1)
    config = SolverConfig(dt_s=args.dt)
    result = solve_problem3(load_environment(attachment1), config)
    workbook_path, table_path = write_outputs(result)

    print(f"attachment1: {attachment1}")
    print(f"drying end time: {result.drying_end_time_s / 3600.0:.4f} h ({result.drying_end_time_s} s)")
    print(
        "coupling convergence: "
        f"{int(result.coupling_converged.sum())}/{len(result.coupling_converged)} steps, "
        f"max iterations {int(result.coupling_iterations.max())}"
    )
    print(f"result workbook: {workbook_path}")
    print(f"paper table: {table_path}")
    print("")
    print(selected_moisture_table(result).to_string(index=False))


if __name__ == "__main__":
    main()
