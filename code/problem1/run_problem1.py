from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from solver import EnvironmentSeries, SolverConfig, solve_problem1


SOURCE_DIR = Path(
    r"D:\电脑管家迁移文件\xwechat_files\wxid_tjlrf4lbc84b22_b62d\msg\file\2026-09\CUMCM2026Problems\A题"
)
ATTACHMENT1 = SOURCE_DIR / "附件" / "附件1.xlsx"
OUTPUT_DIR = Path(__file__).resolve().parents[2] / "results" / "problem1"


def load_environment(path: Path = ATTACHMENT1) -> EnvironmentSeries:
    frame = pd.read_excel(path)
    return EnvironmentSeries(
        time_s=frame["时间"].to_numpy(dtype=float),
        temperature_c=frame["温度"].to_numpy(dtype=float),
        moisture=frame["水分浓度"].to_numpy(dtype=float),
    )


def simulation_to_frame(time_s: np.ndarray, radius_cm: np.ndarray, values: np.ndarray) -> pd.DataFrame:
    data = np.round(values, 4)
    frame = pd.DataFrame(data, columns=[f"{x:.1f}" for x in radius_cm])
    frame.insert(0, "时间\\到药材中心的距离", time_s.astype(int))
    return frame


def selected_table(result, values: np.ndarray, sample_times: list[int], sample_radius_cm: list[float]) -> pd.DataFrame:
    rows = []
    for t in sample_times:
        time_index = int(np.where(result.time_s == t)[0][0])
        row = {"时间/s": t}
        for r in sample_radius_cm:
            radius_index = int(np.where(np.isclose(result.radius_cm, r))[0][0])
            row[f"{r:g} cm"] = round(float(values[time_index, radius_index]), 4)
        rows.append(row)
    return pd.DataFrame(rows)


def _format_markdown_value(value) -> str:
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    return str(value)


def dataframe_to_markdown(frame: pd.DataFrame) -> str:
    headers = [str(column) for column in frame.columns]
    rows = [[_format_markdown_value(value) for value in row] for row in frame.to_numpy()]
    lines = [
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join(["---"] * len(headers)) + " |",
    ]
    lines.extend("| " + " | ".join(row) + " |" for row in rows)
    return "\n".join(lines)


def write_markdown_tables(temp_table: pd.DataFrame, moisture_table: pd.DataFrame, output_dir: Path) -> None:
    text = []
    text.append("# A题第一问论文表格结果")
    text.append("")
    text.append("## 表1 30分钟内药材的温度")
    text.append("")
    text.append(dataframe_to_markdown(temp_table))
    text.append("")
    text.append("## 表2 30分钟内药材的水分浓度")
    text.append("")
    text.append(dataframe_to_markdown(moisture_table))
    text.append("")
    (output_dir / "problem1_tables.md").write_text("\n".join(text), encoding="utf-8")


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    environment = load_environment()
    result = solve_problem1(environment, SolverConfig())

    # The official template starts at 1 s, so the exported workbook follows that layout.
    export_slice = slice(1, None)
    temperature_frame = simulation_to_frame(
        result.time_s[export_slice], result.radius_cm, result.temperature_c[export_slice]
    )
    moisture_frame = simulation_to_frame(
        result.time_s[export_slice], result.radius_cm, result.moisture[export_slice]
    )

    workbook_path = OUTPUT_DIR / "result1.xlsx"
    with pd.ExcelWriter(workbook_path, engine="openpyxl") as writer:
        temperature_frame.to_excel(writer, sheet_name="温度", index=False)
        moisture_frame.to_excel(writer, sheet_name="水分浓度", index=False)

    sample_times = [100, 300, 600, 900, 1200, 1500, 1800]
    sample_radius = [0, 0.5, 1.0, 1.5, 2.0]
    temp_table = selected_table(result, result.temperature_c, sample_times, sample_radius)
    moisture_table = selected_table(result, result.moisture, sample_times, sample_radius)
    write_markdown_tables(temp_table, moisture_table, OUTPUT_DIR)

    print(f"result workbook: {workbook_path}")
    print("")
    print("表1 30分钟内药材的温度")
    print(temp_table.to_string(index=False))
    print("")
    print("表2 30分钟内药材的水分浓度")
    print(moisture_table.to_string(index=False))


if __name__ == "__main__":
    main()
