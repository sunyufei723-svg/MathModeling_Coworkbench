from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from solver import EnvironmentSeries, SolverConfig, solve_problem2


SOURCE_DIR = Path(
    r"D:\电脑管家迁移文件\xwechat_files\wxid_tjlrf4lbc84b22_b62d\msg\file\2026-09\CUMCM2026Problems\A题"
)
ATTACHMENT1 = SOURCE_DIR / "附件" / "附件1.xlsx"
OUTPUT_DIR = Path(__file__).resolve().parents[2] / "results" / "problem2"


def load_environment(path: Path = ATTACHMENT1) -> EnvironmentSeries:
    frame = pd.read_excel(path)
    return EnvironmentSeries(
        time_s=frame["时间"].to_numpy(dtype=float),
        temperature_c=frame["温度"].to_numpy(dtype=float),
        moisture=frame["水分浓度"].to_numpy(dtype=float),
    )


def simulation_to_frame(time_s: np.ndarray, radius_cm: np.ndarray, values: np.ndarray) -> pd.DataFrame:
    data = np.round(values, 4)
    frame = pd.DataFrame(data, columns=[f"{r:.1f}" for r in radius_cm])
    frame.insert(0, "时间\\到药材中心的距离", time_s.astype(int))
    return frame


def selected_table(result, values: np.ndarray, sample_seconds: list[int], sample_radius_cm: list[float]) -> pd.DataFrame:
    rows = []
    for t_s in sample_seconds:
        time_index = int(np.where(result.time_s == t_s)[0][0])
        row = {"时间/h": round(t_s / 3600.0, 1)}
        for radius in sample_radius_cm:
            radius_index = int(np.where(np.isclose(result.radius_cm, radius))[0][0])
            row[f"{radius:g} cm"] = f"{float(values[time_index, radius_index]):.4f}"
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


def write_markdown_tables(temp_table: pd.DataFrame, moisture_table: pd.DataFrame) -> None:
    text = [
        "# A题第二问论文表格结果",
        "",
        "## 表3 3小时内药材的温度",
        "",
        dataframe_to_markdown(temp_table),
        "",
        "## 表4 3小时内药材的水分浓度",
        "",
        dataframe_to_markdown(moisture_table),
        "",
    ]
    (OUTPUT_DIR / "problem2_tables.md").write_text("\n".join(text), encoding="utf-8")


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    result = solve_problem2(load_environment(), SolverConfig())

    export_slice = slice(1, None)
    temperature_frame = simulation_to_frame(
        result.time_s[export_slice], result.radius_cm, result.temperature_c[export_slice]
    )
    moisture_frame = simulation_to_frame(
        result.time_s[export_slice], result.radius_cm, result.moisture[export_slice]
    )

    workbook_path = OUTPUT_DIR / "result2.xlsx"
    with pd.ExcelWriter(workbook_path, engine="openpyxl") as writer:
        temperature_frame.to_excel(writer, sheet_name="温度", index=False)
        moisture_frame.to_excel(writer, sheet_name="水分浓度", index=False)

    sample_seconds = [1800, 3600, 5400, 7200, 9000, 10800]
    sample_radius = [0, 0.5, 1.0, 1.5, 2.0]
    temp_table = selected_table(result, result.temperature_c, sample_seconds, sample_radius)
    moisture_table = selected_table(result, result.moisture, sample_seconds, sample_radius)
    write_markdown_tables(temp_table, moisture_table)

    print(f"result workbook: {workbook_path}")
    print("")
    print("表3 3小时内药材的温度")
    print(temp_table.to_string(index=False))
    print("")
    print("表4 3小时内药材的水分浓度")
    print(moisture_table.to_string(index=False))


if __name__ == "__main__":
    main()
