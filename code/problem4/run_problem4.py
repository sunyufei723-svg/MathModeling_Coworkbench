from __future__ import annotations

import argparse
import os
from pathlib import Path

import numpy as np
import pandas as pd

from solver import EnvironmentSeries, RadiusSeries, SolverConfig, solve_problem4


PROJECT_ROOT = Path(__file__).resolve().parents[2]
OUTPUT_DIR = PROJECT_ROOT / "results" / "problem4"


def resolve_attachment(filename: str, project_root: Path = PROJECT_ROOT, explicit_path: Path | None = None) -> Path:
    """定位 附件1/附件2.xlsx：显式路径 > CUMCM_A_PROBLEM_DIR 环境变量 > 仓库根 附件/ > files/raw。"""
    if explicit_path is not None:
        candidates = [explicit_path]
    else:
        candidates = []
        env_source_dir = os.environ.get("CUMCM_A_PROBLEM_DIR")
        if env_source_dir:
            candidates.append(Path(env_source_dir) / "附件" / filename)
        candidates.append(project_root / "附件" / filename)
        candidates.append(project_root / "files" / "raw" / "CUMCM2026Problems" / "A题" / "附件" / filename)

    for candidate in candidates:
        if candidate.exists():
            return candidate

    searched = "\n".join(str(candidate) for candidate in candidates)
    raise FileNotFoundError(f"未找到 {filename}。请用命令行指定或设置 CUMCM_A_PROBLEM_DIR。\n已搜索：\n{searched}")


def load_environment(path: Path) -> EnvironmentSeries:
    frame = pd.read_excel(path)
    return EnvironmentSeries(
        time_s=frame["时间"].to_numpy(dtype=float),
        temperature_c=frame["温度"].to_numpy(dtype=float),
        moisture=frame["水分浓度"].to_numpy(dtype=float),
    )


def load_radius(path: Path) -> RadiusSeries:
    frame = pd.read_excel(path)
    return RadiusSeries(
        time_s=frame["时间"].to_numpy(dtype=float),
        radius_cm=frame["半径"].to_numpy(dtype=float),
    )


def _moisture_at_distance(profile: np.ndarray, xi: np.ndarray, radius_cm: float, distance_cm: float):
    """Eulerian 固定距离处的水分浓度：ξ=d/R(t) 插值；d>R(t) 时该处已无药材 → NaN。"""
    if distance_cm > radius_cm + 1e-9:
        return np.nan
    return float(np.interp(distance_cm / radius_cm, xi, profile))


def moisture_to_frame(result) -> pd.DataFrame:
    """result4.xlsx：仅水分浓度，固定列 0→1.9 cm（@0.1）+「药材表面」列（移动 R(t)）。"""
    fixed = np.round(np.arange(0.0, 2.0, 0.1), 10)      # 0,0.1,…,1.9（2.0=初始表面由药材表面列承担）
    columns = ["时间\\到药材中心的距离"] + [float(d) for d in fixed] + ["药材表面"]

    rows = []
    for k in range(len(result.time_s)):
        radius_cm = float(result.radius_cm[k])
        profile = result.moisture[k]
        row = [int(round(result.time_s[k]))]
        row.extend(round(_moisture_at_distance(profile, result.xi, radius_cm, float(d)), 4) for d in fixed)
        row.append(round(float(profile[-1]), 4))         # 药材表面 = ξ=1
        rows.append(row)
    return pd.DataFrame(rows, columns=columns)


def selected_moisture_table(result, interval_h: int = 6) -> pd.DataFrame:
    """表6：每 6 h + 烘干结束时间行 × 距离 0,0.5,1.0,1.5 cm +「药材表面」列。"""
    fixed = [0.0, 0.5, 1.0, 1.5]
    sample_seconds = list(range(interval_h * 3600, result.drying_end_time_s + 1, interval_h * 3600))
    if not sample_seconds or sample_seconds[-1] != result.drying_end_time_s:
        sample_seconds.append(result.drying_end_time_s)

    rows = []
    for t_s in sample_seconds:
        source_index = int(np.abs(result.time_s - t_s).argmin())
        radius_cm = float(result.radius_cm[source_index])
        profile = result.moisture[source_index]
        is_end = t_s == result.drying_end_time_s
        row = {"时间/h": "烘干结束时间" if is_end else f"{t_s / 3600.0:.0f}"}
        for distance in fixed:
            value = _moisture_at_distance(profile, result.xi, radius_cm, distance)
            row[f"{distance:g} cm"] = "" if np.isnan(value) else f"{value:.4f}"
        row["药材表面"] = f"{float(profile[-1]):.4f}"
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
    workbook_path = OUTPUT_DIR / "result4.xlsx"
    table_path = OUTPUT_DIR / "problem4_tables.md"

    moisture_frame = moisture_to_frame(result)
    with pd.ExcelWriter(workbook_path, engine="openpyxl") as writer:
        moisture_frame.to_excel(writer, sheet_name="水分浓度", index=False)

    table = selected_moisture_table(result)
    text = [
        "# A题第四问论文表格结果",
        "",
        f"烘干结束时间：{result.drying_end_time_s / 3600.0:.4f} h",
        f"初始半径：{result.radius_cm[0]:.4f} cm；结束半径：{result.radius_cm[-1]:.4f} cm",
        "",
        "## 表6 药材烘干过程的水分浓度（含半径收缩·移动表面）",
        "",
        dataframe_to_markdown(table),
        "",
    ]
    table_path.write_text("\n".join(text), encoding="utf-8")
    return workbook_path, table_path


def main() -> None:
    parser = argparse.ArgumentParser(description="求解 A题第四问（移动边界）并生成 result4.xlsx")
    parser.add_argument("--attachment1", type=Path, default=None, help="附件1.xlsx（烘房温湿）路径")
    parser.add_argument("--attachment2", type=Path, default=None, help="附件2.xlsx（半径收缩）路径")
    parser.add_argument("--dt", type=float, default=10.0, help="内部时间步长，单位 s")
    parser.add_argument("--xi-points", type=int, default=101, help="ξ 网格点数")
    args = parser.parse_args()

    attachment1 = resolve_attachment("附件1.xlsx", explicit_path=args.attachment1)
    attachment2 = resolve_attachment("附件2.xlsx", explicit_path=args.attachment2)
    config = SolverConfig(dt_s=args.dt, xi_points=args.xi_points)
    result = solve_problem4(load_environment(attachment1), load_radius(attachment2), config)
    workbook_path, table_path = write_outputs(result)

    print(f"attachment1: {attachment1}")
    print(f"attachment2: {attachment2}")
    print(f"drying end time: {result.drying_end_time_s / 3600.0:.4f} h ({result.drying_end_time_s} s)")
    print(f"radius: {result.radius_cm[0]:.4f} cm -> {result.radius_cm[-1]:.4f} cm")
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
