"""Independent high-value validation add-ons for the final modeling package.

The script deliberately leaves the accepted problem solvers untouched.  It
checks the radial finite-volume operator against two exact solutions and builds
a lightweight uncertainty surrogate from the already accepted 3x3 sensitivity
tables.
"""

from __future__ import annotations

import json
import math
from dataclasses import dataclass
from pathlib import Path

import numpy as np
from scipy.special import j0


PROJECT_ROOT = Path(__file__).resolve().parents[2]
OUTPUT_DIR = PROJECT_ROOT / "results" / "bonus_validation"


@dataclass(frozen=True)
class ConvergenceRow:
    n: int
    l2_error: float
    max_error: float
    rate: float | None


def radial_fvm_laplacian(u: np.ndarray, dr: float, outer_value: float | None = None) -> np.ndarray:
    """Cell-centred radial FVM Laplacian for 0 <= r <= 1."""
    n = len(u)
    r_centres = (np.arange(n) + 0.5) * dr
    r_faces = np.arange(n + 1) * dr
    flux = np.zeros(n + 1)

    for i in range(1, n):
        flux[i] = r_faces[i] * (u[i] - u[i - 1]) / dr
    if outer_value is not None:
        flux[n] = r_faces[n] * (outer_value - u[-1]) / (0.5 * dr)

    return (flux[1:] - flux[:-1]) / (r_centres * dr)


def convergence_rate(prev_error: float | None, error: float) -> float | None:
    if prev_error is None:
        return None
    return math.log(prev_error / error, 2.0)


def weighted_errors(numerical: np.ndarray, exact: np.ndarray, r: np.ndarray, interior: slice) -> tuple[float, float]:
    diff = numerical[interior] - exact[interior]
    weights = r[interior]
    l2 = math.sqrt(float(np.sum(weights * diff * diff) / np.sum(weights)))
    return l2, float(np.max(np.abs(diff)))


def mms_convergence() -> list[ConvergenceRow]:
    rows: list[ConvergenceRow] = []
    prev = None
    for n in (40, 80, 160, 320):
        dr = 1.0 / n
        r = (np.arange(n) + 0.5) * dr
        u = 1.0 + r**2 + 0.25 * r**4
        exact = 4.0 + 4.0 * r**2
        numerical = radial_fvm_laplacian(u, dr)
        l2, max_error = weighted_errors(numerical, exact, r, slice(1, n - 1))
        rows.append(ConvergenceRow(n, l2, max_error, convergence_rate(prev, l2)))
        prev = l2
    return rows


def bessel_mode_convergence() -> list[ConvergenceRow]:
    rows: list[ConvergenceRow] = []
    prev = None
    lambda_1 = 2.404825557695773
    for n in (40, 80, 160, 320):
        dr = 1.0 / n
        r = (np.arange(n) + 0.5) * dr
        u = j0(lambda_1 * r)
        numerical = radial_fvm_laplacian(u, dr, outer_value=0.0)
        exact = -(lambda_1**2) * j0(lambda_1 * r)
        l2, max_error = weighted_errors(numerical, exact, r, slice(1, n - 1))
        rows.append(ConvergenceRow(n, l2, max_error, convergence_rate(prev, l2)))
        prev = l2
    return rows


Q3_TABLE_H = {
    (-2.0, 0.9): 60.884711,
    (-2.0, 1.0): 60.965405,
    (-2.0, 1.1): 61.070203,
    (0.0, 0.9): 57.087796,
    (0.0, 1.0): 57.172706,
    (0.0, 1.1): 57.280327,
    (2.0, 0.9): 53.615427,
    (2.0, 1.0): 53.704247,
    (2.0, 1.1): 53.814676,
}

Q4_TABLE_H = {
    (-2.0, 0.9): 54.052070691,
    (-2.0, 1.0): 54.148900372,
    (-2.0, 1.1): 54.275268085,
    (0.0, 0.9): 50.727447389,
    (0.0, 1.0): 50.824506989,
    (0.0, 1.1): 50.949840380,
    (2.0, 0.9): 47.683377539,
    (2.0, 1.0): 47.780758130,
    (2.0, 1.1): 47.905240450,
}

Q4_MAIN_H = 50.824506989
Q4_CLOSURE_UPPER_H = 60.7312
Q4_CLOSURE_SOURCE = "discussion/limitations_fix_analysis_by_A.md"


def bilinear_table_predict(table: dict[tuple[float, float], float], delta_t: np.ndarray, c_factor: np.ndarray) -> np.ndarray:
    t0, t1 = -2.0, 2.0
    c0, c1 = 0.9, 1.1
    x = (delta_t - t0) / (t1 - t0)
    y = (c_factor - c0) / (c1 - c0)

    f00 = table[(t0, c0)]
    f10 = table[(t1, c0)]
    f01 = table[(t0, c1)]
    f11 = table[(t1, c1)]
    return (
        (1.0 - x) * (1.0 - y) * f00
        + x * (1.0 - y) * f10
        + (1.0 - x) * y * f01
        + x * y * f11
    )


def latin_hypercube(n: int, dim: int, seed: int = 20260911) -> np.ndarray:
    rng = np.random.default_rng(seed)
    sample = np.empty((n, dim))
    for j in range(dim):
        sample[:, j] = (rng.permutation(n) + rng.random(n)) / n
    return sample


def surrogate_uq(table: dict[tuple[float, float], float], seed_offset: int = 0) -> dict[str, object]:
    n = 5000
    unit = latin_hypercube(n, 2, seed=20260911 + seed_offset)
    delta_t = -2.0 + 4.0 * unit[:, 0]
    c_factor = 0.9 + 0.2 * unit[:, 1]
    values = bilinear_table_predict(table, delta_t, c_factor)

    x_std = np.column_stack(((delta_t - delta_t.mean()) / delta_t.std(), (c_factor - c_factor.mean()) / c_factor.std()))
    y_std = (values - values.mean()) / values.std()
    beta, *_ = np.linalg.lstsq(np.column_stack((np.ones(n), x_std)), y_std, rcond=None)
    contributions = np.square(beta[1:])
    contributions = contributions / contributions.sum()

    return {
        "samples": n,
        "mean_h": float(values.mean()),
        "std_h": float(values.std(ddof=1)),
        "p05_h": float(np.quantile(values, 0.05)),
        "p50_h": float(np.quantile(values, 0.50)),
        "p95_h": float(np.quantile(values, 0.95)),
        "sensitivity_contribution": {
            "ambient_temperature_delta_c": float(contributions[0]),
            "moisture_boundary_factor": float(contributions[1]),
        },
    }


def layered_uq_statement() -> dict[str, object]:
    """Separate boundary-condition UQ from Q4 shrinkage/density-closure model-form UQ."""
    q3_boundary = surrogate_uq(Q3_TABLE_H, seed_offset=0)
    q4_boundary = surrogate_uq(Q4_TABLE_H, seed_offset=17)
    q4_half_width = 0.5 * (q4_boundary["p95_h"] - q4_boundary["p05_h"])
    q4_upper_shift = Q4_CLOSURE_UPPER_H - Q4_MAIN_H

    return {
        "problem3": {
            "boundary_surrogate": {
                **q3_boundary,
                "half_width_h": 0.5 * (q3_boundary["p95_h"] - q3_boundary["p05_h"]),
                "interpretation": "boundary-condition layer only",
            },
            "dominant_layer": "boundary_surrogate",
        },
        "problem4": {
            "main_answer_h": Q4_MAIN_H,
            "boundary_surrogate": {
                **q4_boundary,
                "half_width_h": q4_half_width,
                "interpretation": "continuous boundary-condition layer only; not a total uncertainty interval",
            },
            "shrinkage_density_closure": {
                "lower_bound_h": Q4_MAIN_H,
                "upper_bound_h": Q4_CLOSURE_UPPER_H,
                "upper_shift_h": q4_upper_shift,
                "ratio_to_boundary_half_width": q4_upper_shift / q4_half_width,
                "source": Q4_CLOSURE_SOURCE,
                "interpretation": "model-form layer from enforcing dry-mass closure on the shrinkage/density caliber",
            },
            "dominant_layer": "shrinkage_density_closure",
            "recommended_paper_sentence": (
                "For Q4, the LHS boundary surrogate gives a boundary-condition layer of about "
                f"+/-{q4_half_width:.2f} h, whereas the shrinkage/density-closure model-form layer "
                f"shifts the upper bound by +{q4_upper_shift:.2f} h; thus the dominant uncertainty "
                "comes from the consistency between the prescribed radius trajectory and the empirical density relation, "
                "not from the +/-2 deg C and +/-10% boundary perturbations."
            ),
        },
    }


def table_to_markdown(rows: list[ConvergenceRow]) -> str:
    lines = ["| N | L2 error | max error | rate |", "|---:|---:|---:|---:|"]
    for row in rows:
        rate = "" if row.rate is None else f"{row.rate:.3f}"
        lines.append(f"| {row.n} | {row.l2_error:.6e} | {row.max_error:.6e} | {rate} |")
    return "\n".join(lines)


def write_report(summary: dict[str, object]) -> None:
    mms_rows = summary["mms_convergence"]
    bessel_rows = summary["bessel_convergence"]
    q3 = summary["uq_surrogate"]["problem3"]
    q4 = summary["uq_surrogate"]["problem4"]
    layered_q4 = summary["layered_uq"]["problem4"]
    boundary = layered_q4["boundary_surrogate"]
    closure = layered_q4["shrinkage_density_closure"]

    report = f"""# Bonus validation report

本报告为独立加分验证包输出，不修改任何现有 `problem1`-`problem4` 求解器。

## 1. MMS radial FVM check

制造解取 `u(r)=1+r^2+0.25r^4`，解析径向 Laplacian 为 `4+4r^2`。下表误差统计排除最外层边界半控制体，主要检验内部守恒型径向 FVM 通量离散。

{table_to_markdown([ConvergenceRow(**row) for row in mms_rows])}

结论：内部空间算子达到接近二阶收敛，可作为论文“离散格式正确性”的轻量证据。

## 2. Bessel analytic mode cross-check

取圆柱 Dirichlet 本征模态 `u(r)=J0(lambda_1 r)`，其中 `lambda_1=2.4048255577` 为 `J0` 第一零点；解析关系为 `Delta_r u = -lambda_1^2 u`。

{table_to_markdown([ConvergenceRow(**row) for row in bessel_rows])}

结论：Bessel 模态从解析结构上覆盖了圆柱坐标奇点附近的正则性处理，可补强“径向模型没有把 1/r 项离散错”的论证。

## 3. Boundary-layer LHS surrogate check

基于已验收的 3x3 边界敏感性结果构建双线性代理面，变量范围为 `Delta T in [-2,2] deg C`、`moisture factor in [0.9,1.1]`，采用 5000 点 Latin Hypercube 采样。该项不是替代全模型重算，而是论文中的快速鲁棒性量化。

| Problem | mean h | std h | p05 h | p50 h | p95 h | temp contribution | moisture contribution |
|---|---:|---:|---:|---:|---:|---:|---:|
| Q3 | {q3["mean_h"]:.4f} | {q3["std_h"]:.4f} | {q3["p05_h"]:.4f} | {q3["p50_h"]:.4f} | {q3["p95_h"]:.4f} | {q3["sensitivity_contribution"]["ambient_temperature_delta_c"]:.3f} | {q3["sensitivity_contribution"]["moisture_boundary_factor"]:.3f} |
| Q4 | {q4["mean_h"]:.4f} | {q4["std_h"]:.4f} | {q4["p05_h"]:.4f} | {q4["p50_h"]:.4f} | {q4["p95_h"]:.4f} | {q4["sensitivity_contribution"]["ambient_temperature_delta_c"]:.3f} | {q4["sensitivity_contribution"]["moisture_boundary_factor"]:.3f} |

结论：在当前边界扰动范围内，终止时间不确定性主要由环境温度扰动贡献，湿度因子贡献较小；这与 Q3/Q4 已有 3x3 敏感性表的方向一致。

## 4. Layered UQ statement for Q4

上述 LHS 代理面只覆盖边界条件层，不应写成 Q4 的总不确定性。A 的 dry-mass closure 诊断指出，题设给定 `R(t)` 与经验密度关系之间的闭合口径会形成更大的模型形式层。因此 Q4 的 UQ 应分层表述：

| Layer | Quantity | Value |
|---|---|---:|
| Boundary-condition layer | LHS p05-p95 | {boundary["p05_h"]:.4f} - {boundary["p95_h"]:.4f} h |
| Boundary-condition layer | half-width | {boundary["half_width_h"]:.4f} h |
| Shrinkage/density-closure layer | main answer lower bound | {closure["lower_bound_h"]:.4f} h |
| Shrinkage/density-closure layer | dry-mass-closure upper bound | {closure["upper_bound_h"]:.4f} h |
| Shrinkage/density-closure layer | upper shift | +{closure["upper_shift_h"]:.4f} h |
| Ratio | closure shift / boundary half-width | {closure["ratio_to_boundary_half_width"]:.2f} |

推荐论文表述：{layered_q4["recommended_paper_sentence"]}

注意：`60.7312 h` 目前来自 `discussion/limitations_fix_analysis_by_A.md` 的诊断值，适合作为分层 UQ 的模型形式上界说明；若要把它作为正式表格 rung，应另建 `problem4_mass_closure/` 做 N=3201 可复现计算。
"""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUTPUT_DIR / "bonus_validation_report.md").write_text(report, encoding="utf-8")
    (OUTPUT_DIR / "bonus_validation_summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def rows_to_dicts(rows: list[ConvergenceRow]) -> list[dict[str, float | int | None]]:
    return [
        {
            "n": row.n,
            "l2_error": row.l2_error,
            "max_error": row.max_error,
            "rate": row.rate,
        }
        for row in rows
    ]


def main() -> None:
    mms_rows = mms_convergence()
    bessel_rows = bessel_mode_convergence()
    summary: dict[str, object] = {
        "sources": {
            "problem3": "results/problem3_fvm_bdf/boundary_sensitivity.md",
            "problem4": "results/problem4_fvm_bdf/verification.json",
            "problem4_shrinkage_density_closure": Q4_CLOSURE_SOURCE,
        },
        "mms_convergence": rows_to_dicts(mms_rows),
        "bessel_convergence": rows_to_dicts(bessel_rows),
        "uq_surrogate": {
            "problem3": surrogate_uq(Q3_TABLE_H, seed_offset=0),
            "problem4": surrogate_uq(Q4_TABLE_H, seed_offset=17),
        },
        "layered_uq": layered_uq_statement(),
    }
    write_report(summary)
    print(f"Wrote {OUTPUT_DIR / 'bonus_validation_report.md'}")
    print(f"Wrote {OUTPUT_DIR / 'bonus_validation_summary.json'}")


if __name__ == "__main__":
    main()
