from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

import numpy as np

from solver import EnvironmentSeries, SolverConfig, solve_problem1


SAMPLE_TIMES = [100, 300, 600, 900, 1200, 1500, 1800]
SAMPLE_RADII_CM = [0.0, 0.5, 1.0, 1.5, 2.0]


def load_environment(path: Path) -> EnvironmentSeries:
    """Load the three-column environment data emitted by extract_environment.mjs."""

    if path.suffix.lower() == ".json":
        payload = json.loads(path.read_text(encoding="utf-8"))
        rows = payload["rows"]
    elif path.suffix.lower() == ".csv":
        with path.open("r", encoding="utf-8-sig", newline="") as handle:
            rows = list(csv.DictReader(handle))
    else:
        raise ValueError("environment input must be .json or .csv")

    def column(*names: str) -> np.ndarray:
        for name in names:
            if rows and name in rows[0]:
                return np.asarray([float(row[name]) for row in rows], dtype=float)
        raise KeyError(f"missing environment column; expected one of {names}")

    return EnvironmentSeries(
        time_s=column("时间", "time_s"),
        temperature_c=column("温度", "temperature_c"),
        moisture=column("水分浓度", "moisture"),
    )


def selected_values(result, values: np.ndarray) -> list[list[float]]:
    rows: list[list[float]] = []
    for sample_time in SAMPLE_TIMES:
        time_index = int(np.where(np.isclose(result.time_s, sample_time))[0][0])
        row = [float(sample_time)]
        for radius in SAMPLE_RADII_CM:
            radius_index = int(np.where(np.isclose(result.radius_cm, radius))[0][0])
            row.append(float(values[time_index, radius_index]))
        rows.append(row)
    return rows


def markdown_table(headers: list[str], rows: list[list[float]]) -> str:
    lines = [
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join(["---:"] * len(headers)) + " |",
    ]
    for row in rows:
        cells = [str(int(row[0]))] + [f"{value:.4f}" for value in row[1:]]
        lines.append("| " + " | ".join(cells) + " |")
    return "\n".join(lines)


def write_tables(result, output_path: Path) -> None:
    headers = ["时间/s", "0 cm", "0.5 cm", "1 cm", "1.5 cm", "2 cm"]
    temperature_rows = selected_values(result, result.temperature_c)
    moisture_rows = selected_values(result, result.moisture)
    text = [
        "# A题第一问论文表格结果（修正版）",
        "",
        "> 计算方法：一维径向守恒型有限体积法；内部网格 0.0025 cm；BDF 隐式时间积分。",
        "",
        "## 表1 30分钟内药材的温度 / °C",
        "",
        markdown_table(headers, temperature_rows),
        "",
        "## 表2 30分钟内药材的水分浓度 / kg·kg⁻¹",
        "",
        markdown_table(headers, moisture_rows),
        "",
    ]
    output_path.write_text("\n".join(text), encoding="utf-8")


def write_payload(result, output_path: Path) -> None:
    export_slice = slice(1, None)  # Official template begins at t=1 s.
    payload = {
        "time_s": result.time_s[export_slice].astype(int).tolist(),
        "radius_cm": [round(float(value), 10) for value in result.radius_cm],
        "temperature_c": np.round(result.temperature_c[export_slice], 10).tolist(),
        "moisture": np.round(result.moisture[export_slice], 10).tolist(),
        "metadata": {
            "method": "radial finite volume method + BDF",
            "internal_dr_cm": 0.0025,
            "output_dr_cm": 0.1,
            "output_dt_s": 1.0,
            "diffusivity": "D(C)=7e-9*exp(-0.89/C)",
        },
    }
    output_path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Solve CUMCM A problem 1")
    parser.add_argument("--environment", type=Path, required=True, help="boundary data (.json or .csv)")
    parser.add_argument("--payload", type=Path, required=True, help="JSON payload for workbook export")
    parser.add_argument(
        "--tables",
        type=Path,
        default=Path(__file__).resolve().parents[2] / "results" / "problem1" / "problem1_tables.md",
        help="Markdown result table path",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    environment = load_environment(args.environment)
    result = solve_problem1(environment, SolverConfig())
    args.payload.parent.mkdir(parents=True, exist_ok=True)
    args.tables.parent.mkdir(parents=True, exist_ok=True)
    write_payload(result, args.payload)
    write_tables(result, args.tables)
    print(f"payload: {args.payload}")
    print(f"tables: {args.tables}")
    print("temperature at 1800 s:", np.round(result.temperature_c[-1, [0, 5, 10, 15, 20]], 4))
    print("moisture at 1800 s:", np.round(result.moisture[-1, [0, 5, 10, 15, 20]], 4))


if __name__ == "__main__":
    main()
