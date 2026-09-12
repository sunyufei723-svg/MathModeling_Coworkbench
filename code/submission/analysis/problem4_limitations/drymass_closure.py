"""局限性分析诊断脚本（已收入 code/problem4_limitations/）。

目的：把 problem4_fvm_bdf 报告的 dry_mass_index_relative_range = 28.02% 做成因分解，
并用「干物质闭合」不动点迭代检验该局限是否可消除、对 t* 影响多大。

只读调用现有求解器，不修改 code/ 与 results/ 下任何文件。
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[4]   # 仓库根（脚本在 code/submission/analysis/problem4_limitations/）
# 让 stdout/stderr 用 UTF-8，避免 Windows 管道/重定向下 GBK 编码崩溃（脚本含 ⇒ κ ρ ⟨⟩ 等字符）
for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8")
    except (AttributeError, ValueError):
        pass
sys.path.insert(0, str(ROOT / "code" / "submission" / "pipeline" / "problem4"))
sys.path.insert(0, str(ROOT / "code" / "submission" / "business" / "problem4"))

from fvm import build_reference_geometry  # noqa: E402
from model import density  # noqa: E402
from radius import RadiusSeries  # noqa: E402
from run_and_verify import load_inputs  # noqa: E402
from solver_bdf import SolverConfig, solve_problem4_bdf  # noqa: E402

NODE = 401
CFG = SolverConfig(node_count=NODE)
GEO = build_reference_geometry(NODE)
VHAT_SUM = float(np.sum(GEO.volumes_hat))
C0 = CFG.initial_moisture
RHO_S0 = float(density(C0) / (1.0 + C0))
R0_CM = 2.0


def dry_density(c: np.ndarray | float) -> np.ndarray:
    """干基固体密度 rho_s(C) = rho_bulk(C)/(1+C)，C 为干基含水率。"""
    return density(c) / (1.0 + np.asarray(c, dtype=float))


def equivalent_uniform_moisture(rho_s_mean: float) -> float:
    """把体积平均干基密度反解成「等效均匀含水率」，便于物理解读。"""
    return (rho_s_mean - 760.0) / (90.0 - rho_s_mean)


def analyse(label: str, radius: RadiusSeries) -> dict:
    res = solve_problem4_bdf(ENV, radius, CFG)
    t_h = res.time_s / 3600.0
    r_cm = res.radius_cm
    m = res.dry_mass_index                      # = R^2 * sum(rho_s(C) Vhat)
    m0 = (R0_CM / 100.0) ** 2 * RHO_S0 * VHAT_SUM
    kappa = m / m0                              # 干物质闭合偏差
    geo_fac = (r_cm / R0_CM) ** 2
    rho_s_mean = m / ((r_cm / 100.0) ** 2 * VHAT_SUM)
    comp_fac = rho_s_mean / RHO_S0
    i_min = int(np.argmin(kappa))
    out = {
        "label": label,
        "t_star_h": res.drying_event_time_s / 3600.0,
        "rel_range": float((kappa.max() - kappa.min()) / abs(kappa[0])),
        "kappa_min": float(kappa[i_min]),
        "t_kappa_min_h": float(t_h[i_min]),
        "kappa_event": float(kappa[-1]),
        "R_event_cm": float(res.event_radius_cm),
        "geo_event": float(geo_fac[-1]),
        "comp_event": float(comp_fac[-1]),
        "C_eq_event": float(equivalent_uniform_moisture(rho_s_mean[-1])),
        "max_C_event": float(res.max_moisture[-1]),
        "kappa_series": kappa,
        "comp_series": comp_fac,
        "t_h": t_h,
        "r_cm": r_cm,
    }
    print(f"[{label}] t*={out['t_star_h']:.6f} h  kappa_rel_range={out['rel_range']:.4%}")
    print(f"    kappa_min={out['kappa_min']:.6f} @ t={out['t_kappa_min_h']:.4f} h"
          f"   kappa(event)={out['kappa_event']:.6f}")
    print(f"    event: R={out['R_event_cm']:.4f} cm  G=(R/R0)^2={out['geo_event']:.6f}"
          f"  S=<rho_s>/rho_s0={out['comp_event']:.6f}  G*S={out['geo_event']*out['comp_event']:.6f}")
    print(f"    event: C_eq(from <rho_s>)={out['C_eq_event']:.6f}  max C={out['max_C_event']:.6f}")
    return out


ENV, RAD_GIVEN = load_inputs(ROOT / "附件" / "附件1.xlsx", ROOT / "附件" / "附件2.xlsx")
print(f"rho_s0 = rho(C0)/(1+C0) = {RHO_S0:.6f} kg/m^3   (C0={C0})")
print(f"rho_s(0.15) = {float(dry_density(0.15)):.4f}   rho_s(0.0525) = {float(dry_density(0.0525)):.4f}")
print(f"sum(Vhat) = {VHAT_SUM:.6f}   R0 = {R0_CM} cm   N = {NODE}")
print(f"附件2: t_end={RAD_GIVEN.terminal_time_s:.0f} s, R(0)={RAD_GIVEN.radius_cm[0]}, R(end)={RAD_GIVEN.radius_cm[-1]}")
print("=" * 78)

base = analyse("iter0 given R(t)", RAD_GIVEN)

# ---- 干物质闭合不动点迭代：R_{k+1}(t) = R0 / sqrt(S_k(t)) ----
prev = base
for k in range(1, 4):
    s = prev["comp_series"]
    t = np.concatenate([[0.0], prev["t_h"] * 3600.0])
    r_new = R0_CM / np.sqrt(np.concatenate([[1.0], s]))
    if np.any(np.diff(t) <= 0):
        raise RuntimeError("closure time grid not strictly increasing")
    series = RadiusSeries(t, r_new, "linear")
    cur = analyse(f"iter{k} closure R(t)", series)
    dr = float(np.max(np.abs(cur["r_cm"] - np.interp(cur["t_h"] * 3600.0, t, r_new))))
    print(f"    R-change vs previous iterate: max|dR|={dr:.3e} cm"
          f"   dt*={cur['t_star_h']-prev['t_star_h']:+.6f} h"
          f"   R(end of series)={r_new[-1]:.4f} cm")
    print("-" * 78)
    if abs(cur["t_star_h"] - prev["t_star_h"]) < 1e-4 and cur["rel_range"] < 1e-4:
        print("    converged")
        prev = cur
        break
    prev = cur

print("=" * 78)
print("SUMMARY")
print(f"given-R t* (N={NODE})      = {base['t_star_h']:.6f} h   kappa range = {base['rel_range']:.4%}")
print(f"closure t* (final iterate) = {prev['t_star_h']:.6f} h   kappa range = {prev['rel_range']:.4%}")
print(f"delta t* = {prev['t_star_h']-base['t_star_h']:+.6f} h "
      f"({(prev['t_star_h']-base['t_star_h'])/base['t_star_h']:+.4%})")
# 早期/后期路径对照：给定 R(t) vs 闭合 R(t)
for th in (1.0, 4.0, 12.0, 24.0, 48.0):
    i = int(np.argmin(np.abs(base["t_h"] - th)))
    print(f"  t={base['t_h'][i]:7.2f} h  R_given={base['r_cm'][i]:.4f} cm  "
          f"kappa={base['kappa_series'][i]:.6f}  S={base['comp_series'][i]:.6f}  "
          f"R_closure={R0_CM/np.sqrt(base['comp_series'][i]):.4f} cm")
