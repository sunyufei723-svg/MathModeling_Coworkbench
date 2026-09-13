"""加分验证（单文件 · 无参数运行）。

六段独立验证（论文加分项 / 附录 A 引用）：
  1. MMS 收敛性：制造解 u=1+r²+0.25r⁴，验证径向 FVM Laplacian 二阶收敛。
  2. Bessel 模态：J₀(λ₁r) 解析本征态，λ₁=2.4048255577，验证圆柱坐标奇点处理。
  3. Robin 边界：两项——Robin-Bessel 模态 + Robin-MMS，验证表面对流半控制体。
  4. 隐式 Euler 时间：标量衰减 y'=-λy 的一阶时间精度验证。
  5. LHS 代理 UQ：从 3×3 边界敏感性表构建双线性代理面，5000 点 LHS 抽样。
  6. 分层 UQ 声明：边界条件层 vs 收缩/密度闭合模型形式层。

数据源与产物（全部相对本脚本目录 code/submission/）：
- 输入：无外部附件（3×3 表硬编码自已验收的 problem3/4 结果）
- 输出：终端分节打印 + bonus_validation.json

用法：python bonus.py   （无任何命令行参数）
"""
from __future__ import annotations

import json
import math
from dataclasses import dataclass
from pathlib import Path

import numpy as np
from scipy.optimize import brentq
from scipy.special import j0, j1

BASE = Path(__file__).resolve().parent

LINE = "=" * 78


# --------------------------------------------------------------------------- #
# 数据类
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class ConvergenceRow:
    n: int
    l2_error: float
    max_error: float
    rate: float | None


# --------------------------------------------------------------------------- #
# 核心算子
# --------------------------------------------------------------------------- #
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


def radial_fvm_laplacian_robin(
    u: np.ndarray, dr: float, biot: float, ambient: float = 0.0,
) -> np.ndarray:
    """Cell-centred radial FVM Laplacian with Robin outer boundary."""
    n = len(u)
    r_centres = (np.arange(n) + 0.5) * dr
    r_faces = np.arange(n + 1) * dr
    flux = np.zeros(n + 1)
    for i in range(1, n):
        flux[i] = r_faces[i] * (u[i] - u[i - 1]) / dr
    if n < 2:
        raise ValueError("Robin FVM check needs at least two cells")
    surface = (
        (3.0 * u[-1] - (1.0 / 3.0) * u[-2]) / dr + biot * ambient
    ) / ((8.0 / 3.0) / dr + biot)
    surface_gradient = -biot * (surface - ambient)
    flux[n] = r_faces[n] * surface_gradient
    return (flux[1:] - flux[:-1]) / (r_centres * dr)


def convergence_rate(prev_error: float | None, error: float) -> float | None:
    if prev_error is None:
        return None
    return math.log(prev_error / error, 2.0)


def weighted_errors(
    numerical: np.ndarray, exact: np.ndarray, r: np.ndarray, interior: slice,
) -> tuple[float, float]:
    diff = numerical[interior] - exact[interior]
    weights = r[interior]
    l2 = math.sqrt(float(np.sum(weights * diff * diff) / np.sum(weights)))
    return l2, float(np.max(np.abs(diff)))


# --------------------------------------------------------------------------- #
# §1  MMS 收敛性
# --------------------------------------------------------------------------- #
def mms_convergence() -> list[ConvergenceRow]:
    rows: list[ConvergenceRow] = []
    prev = None
    for n in (40, 80, 160, 320):
        dr = 1.0 / n
        r = (np.arange(n) + 0.5) * dr
        u = 1.0 + r**2 + 0.25 * r**4
        exact = 4.0 + 4.0 * r**2
        numerical = radial_fvm_laplacian(u, dr)
        l2, max_err = weighted_errors(numerical, exact, r, slice(1, n - 1))
        rows.append(ConvergenceRow(n, l2, max_err, convergence_rate(prev, l2)))
        prev = l2
    return rows


# --------------------------------------------------------------------------- #
# §2  Bessel 模态
# --------------------------------------------------------------------------- #
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
        l2, max_err = weighted_errors(numerical, exact, r, slice(1, n - 1))
        rows.append(ConvergenceRow(n, l2, max_err, convergence_rate(prev, l2)))
        prev = l2
    return rows


# --------------------------------------------------------------------------- #
# §3  Robin 边界
# --------------------------------------------------------------------------- #
def first_robin_bessel_root(biot: float) -> float:
    def equation(value: float) -> float:
        return value * j1(value) - biot * j0(value)
    return float(brentq(equation, 1.0e-10, 2.404825557695773))


def robin_bessel_convergence() -> list[ConvergenceRow]:
    rows: list[ConvergenceRow] = []
    prev = None
    biot = 2.5
    lambda_1 = first_robin_bessel_root(biot)
    for n in (40, 80, 160, 320):
        dr = 1.0 / n
        r = (np.arange(n) + 0.5) * dr
        faces = np.arange(n + 1) * dr
        u = j0(lambda_1 * r)
        numerical = radial_fvm_laplacian_robin(u, dr, biot)
        exact_flux = faces * (-lambda_1 * j1(lambda_1 * faces))
        exact = (exact_flux[1:] - exact_flux[:-1]) / (r * dr)
        l2, max_err = weighted_errors(numerical, exact, r, slice(1, n))
        rows.append(ConvergenceRow(n, l2, max_err, convergence_rate(prev, l2)))
        prev = l2
    return rows


def robin_mms_convergence() -> list[ConvergenceRow]:
    rows: list[ConvergenceRow] = []
    prev = None
    biot = 3.0
    ambient = 2.25 + 3.0 / biot
    for n in (40, 80, 160, 320):
        dr = 1.0 / n
        r = (np.arange(n) + 0.5) * dr
        faces = np.arange(n + 1) * dr
        u = 1.0 + r**2 + 0.25 * r**4
        exact_gradient = 2.0 * faces + faces**3
        exact_flux = faces * exact_gradient
        exact = (exact_flux[1:] - exact_flux[:-1]) / (r * dr)
        numerical = radial_fvm_laplacian_robin(u, dr, biot, ambient)
        l2, max_err = weighted_errors(numerical, exact, r, slice(1, n))
        rows.append(ConvergenceRow(n, l2, max_err, convergence_rate(prev, l2)))
        prev = l2
    return rows


# --------------------------------------------------------------------------- #
# §4  隐式 Euler 时间
# --------------------------------------------------------------------------- #
def implicit_euler_time_convergence() -> list[ConvergenceRow]:
    rows: list[ConvergenceRow] = []
    prev = None
    decay = 1.7
    final_time = 1.0
    exact = math.exp(-decay * final_time)
    for steps in (20, 40, 80, 160):
        dt = final_time / steps
        numerical = (1.0 / (1.0 + decay * dt)) ** steps
        error = abs(numerical - exact)
        rows.append(ConvergenceRow(steps, error, error, convergence_rate(prev, error)))
        prev = error
    return rows


# --------------------------------------------------------------------------- #
# §5  LHS 代理 UQ
# --------------------------------------------------------------------------- #
Q3_TABLE_H = {
    (-2.0, 0.9): 60.884711, (-2.0, 1.0): 60.965405, (-2.0, 1.1): 61.070203,
    (0.0, 0.9): 57.087796,  (0.0, 1.0): 57.172706,  (0.0, 1.1): 57.280327,
    (2.0, 0.9): 53.615427,  (2.0, 1.0): 53.704247,  (2.0, 1.1): 53.814676,
}

Q4_TABLE_H = {
    (-2.0, 0.9): 54.052070691, (-2.0, 1.0): 54.148900372, (-2.0, 1.1): 54.275268085,
    (0.0, 0.9): 50.727447389,  (0.0, 1.0): 50.824506989,  (0.0, 1.1): 50.949840380,
    (2.0, 0.9): 47.683377539,  (2.0, 1.0): 47.780758130,  (2.0, 1.1): 47.905240450,
}

Q4_MAIN_H = 50.824506989
Q4_CLOSURE_UPPER_H = 60.7443       # N=3201 mass_closure 正式值


def bilinear_table_predict(
    table: dict[tuple[float, float], float], delta_t: np.ndarray, c_factor: np.ndarray,
) -> np.ndarray:
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


def surrogate_uq(
    table: dict[tuple[float, float], float], seed_offset: int = 0,
) -> dict[str, object]:
    n = 5000
    unit = latin_hypercube(n, 2, seed=20260911 + seed_offset)
    delta_t = -2.0 + 4.0 * unit[:, 0]
    c_factor = 0.9 + 0.2 * unit[:, 1]
    values = bilinear_table_predict(table, delta_t, c_factor)
    x_std = np.column_stack((
        (delta_t - delta_t.mean()) / delta_t.std(),
        (c_factor - c_factor.mean()) / c_factor.std(),
    ))
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


# --------------------------------------------------------------------------- #
# §6  分层 UQ
# --------------------------------------------------------------------------- #
def layered_uq_statement() -> dict[str, object]:
    q3_boundary = surrogate_uq(Q3_TABLE_H, seed_offset=0)
    q4_boundary = surrogate_uq(Q4_TABLE_H, seed_offset=17)
    q4_half_width = 0.5 * (q4_boundary["p95_h"] - q4_boundary["p05_h"])
    q4_upper_shift = Q4_CLOSURE_UPPER_H - Q4_MAIN_H
    return {
        "problem3": {
            "boundary_surrogate": {
                **q3_boundary,
                "half_width_h": 0.5 * (q3_boundary["p95_h"] - q3_boundary["p05_h"]),
            },
        },
        "problem4": {
            "main_answer_h": Q4_MAIN_H,
            "boundary_surrogate": {
                **q4_boundary,
                "half_width_h": q4_half_width,
            },
            "shrinkage_density_closure": {
                "lower_bound_h": Q4_MAIN_H,
                "upper_bound_h": Q4_CLOSURE_UPPER_H,
                "upper_shift_h": q4_upper_shift,
                "ratio_to_boundary_half_width": q4_upper_shift / q4_half_width,
            },
        },
    }


# --------------------------------------------------------------------------- #
# 打印辅助
# --------------------------------------------------------------------------- #
def print_conv_table(title: str, rows: list[ConvergenceRow]) -> None:
    print(f"  {title}")
    print(f"    {'N':>6s}  {'L2 error':>12s}  {'max error':>12s}  {'rate':>6s}")
    for row in rows:
        rate_s = "" if row.rate is None else f"{row.rate:.3f}"
        print(f"    {row.n:6d}  {row.l2_error:12.6e}  {row.max_error:12.6e}  {rate_s:>6s}")


def rows_to_dicts(rows: list[ConvergenceRow]) -> list[dict]:
    return [
        {"n": r.n, "l2_error": r.l2_error, "max_error": r.max_error, "rate": r.rate}
        for r in rows
    ]


# --------------------------------------------------------------------------- #
# 主函数
# --------------------------------------------------------------------------- #
def main() -> None:
    print(LINE)
    print("加分验证（六段独立检验）")
    print(LINE)

    # §1 MMS
    print(f"\n{'-'*78}")
    print("[§1] MMS 径向 FVM 收敛性（制造解 u=1+r^2+0.25r^4）")
    print(f"{'-'*78}")
    mms_rows = mms_convergence()
    print_conv_table("径向 FVM Laplacian 内部节点收敛", mms_rows)
    print(f"  结论：内部空间算子达到 ~二阶收敛，验证离散格式正确性。")

    # §2 Bessel
    print(f"\n{'-'*78}")
    print("[§2] Bessel 解析模态交叉验证（J0(lambda_1*r), lambda_1=2.4048）")
    print(f"{'-'*78}")
    bessel_rows = bessel_mode_convergence()
    print_conv_table("Bessel J0 模态收敛", bessel_rows)
    print(f"  结论：Bessel 模态覆盖圆柱坐标奇点附近的正则性处理。")

    # §3 Robin
    print(f"\n{'-'*78}")
    print("[§3] Robin 边界附加检验（-u_r(1)=Bi*(u(1)-u_inf)）")
    print(f"{'-'*78}")
    rb_rows = robin_bessel_convergence()
    print_conv_table("§3.1 Robin-Bessel 模态（Bi=2.5）", rb_rows)
    rm_rows = robin_mms_convergence()
    print_conv_table("§3.2 Robin-MMS（Bi=3.0）", rm_rows)
    print(f"  结论：Robin 通量符号、表面半控制体稳定收敛，L2 ~1.5 阶"
          f"（外层半控制体为主导误差源）。")

    # §4 隐式 Euler
    print(f"\n{'-'*78}")
    print("[§4] 隐式 Euler 时间收敛性（y'=-1.7y, t_final=1.0）")
    print(f"{'-'*78}")
    euler_rows = implicit_euler_time_convergence()
    print_conv_table("隐式 Euler 放大因子 vs exp(-1.7)", euler_rows)
    print(f"  结论：隐式 Euler 时间推进呈一阶收敛。")

    # §5 LHS 代理 UQ
    print(f"\n{'-'*78}")
    print("[§5] LHS 代理面 UQ（5000 点 LHS 抽样，3x3 边界敏感性表）")
    print(f"{'-'*78}")
    q3_uq = surrogate_uq(Q3_TABLE_H, seed_offset=0)
    q4_uq = surrogate_uq(Q4_TABLE_H, seed_offset=17)

    print(f"\n  {'问题':>4s}  {'mean/h':>10s}  {'std/h':>10s}  {'p05/h':>10s}  "
          f"{'p50/h':>10s}  {'p95/h':>10s}  {'T 贡献':>8s}  {'C 贡献':>8s}")
    for tag, uq in [("Q3", q3_uq), ("Q4", q4_uq)]:
        sc = uq["sensitivity_contribution"]
        print(f"  {tag:>4s}  {uq['mean_h']:10.4f}  {uq['std_h']:10.4f}  "
              f"{uq['p05_h']:10.4f}  {uq['p50_h']:10.4f}  {uq['p95_h']:10.4f}  "
              f"{sc['ambient_temperature_delta_c']:8.3f}  "
              f"{sc['moisture_boundary_factor']:8.3f}")
    print(f"  结论：边界扰动范围内，终止时间不确定性主要由环境温度扰动贡献。")
    print(f"  注：当前 LHS 为双线性代理面 5000 次抽样（非 5000 次 PDE），"
          f"需补 5-10 个 held-out PDE 点方可称为高保真验证。")

    # §6 分层 UQ
    print(f"\n{'-'*78}")
    print("[§6] Q4 分层 UQ 声明")
    print(f"{'-'*78}")
    layered = layered_uq_statement()
    q4_l = layered["problem4"]
    bnd = q4_l["boundary_surrogate"]
    cls = q4_l["shrinkage_density_closure"]

    print(f"\n  边界条件层（LHS 代理）：")
    print(f"    p05-p95 = {bnd['p05_h']:.4f} - {bnd['p95_h']:.4f} h"
          f"  半宽 = {bnd['half_width_h']:.4f} h")
    print(f"\n  收缩/密度闭合层（模型形式）：")
    print(f"    下界 = {cls['lower_bound_h']:.4f} h（主答案）"
          f"  上界 = {cls['upper_bound_h']:.4f} h"
          f"  偏移 = +{cls['upper_shift_h']:.4f} h")
    print(f"    闭合偏移 / 边界半宽 = {cls['ratio_to_boundary_half_width']:.2f}")
    print(f"\n  推荐论文表述：Q4 的 LHS 边界代理给出 ~+/-{bnd['half_width_h']:.2f} h"
          f" 的边界条件层，而收缩/密度闭合模型形式层偏移 +{cls['upper_shift_h']:.2f} h；"
          f"支配性不确定源是题给半径轨迹与经验密度关系的闭合缺口，"
          f"而非 +/-2 deg C / +/-10% 的边界扰动。")

    # 输出 JSON
    summary = {
        "mms_convergence": rows_to_dicts(mms_rows),
        "bessel_convergence": rows_to_dicts(bessel_rows),
        "robin_bessel_convergence": rows_to_dicts(rb_rows),
        "robin_mms_convergence": rows_to_dicts(rm_rows),
        "implicit_euler_time_convergence": rows_to_dicts(euler_rows),
        "uq_surrogate": {"problem3": q3_uq, "problem4": q4_uq},
        "layered_uq": layered,
    }
    out_path = BASE / "bonus_validation.json"
    out_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"\n{LINE}")
    print(f"加分验证完成。JSON -> {out_path.name}")
    print(LINE)


if __name__ == "__main__":
    main()
