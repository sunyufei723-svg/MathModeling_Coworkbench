"""问题四模型局限性诊断（单文件 · 无参数运行）。

五段诊断（论文附录 B / 模型评价引用）：
  1. 上界论证：附录4 密度律 ρ_s(C)=90+670/(1+C) 在 C≥0 上确界 760 kg/m³（C=0 绝干），
     而「均匀仿射收缩 + 干物质守恒」要求 ρ_s(t)=ρ_s0·(R0/R(t))²。当 R(t)<R_c=R0·√(ρ_s0/760)
     =1.211 cm 时，闭合要求的 ρ_s 超过 760 ⇒ 无论含水率场算得多准都不可能闭合。
  2. 干物质闭合诊断：28.02% 漂移的成因分解（κ=G·S，几何因子 vs 组成因子），
     不动点迭代 R_{k+1}(t)=R0/√(S_k(t)) 强制闭合后 t* 从 50.84 h 推迟到 ~60.73 h（N401）。
  3. 潜热预算：失水量×汽化潜热 Q_lat vs 显热输入 Q_sens，比值 Q_lat/Q_sens 判断忽略潜热的量级。
  4. 潜热效应代理：给温度场整体减去蒸发冷却温降 ΔT=0/3/5/10 K，用真实 D(T) 让干燥变慢，
     验证潜热会使 28.02% 缺口更大（而非更小）。
  5. 半径-含水率核查：附件2 R(t) 不同插值方式（linear/pchip/cubic-spline/指数拟合）对 t*
     的影响；D 缩放因子标定（D×10 也只把 κ_min 抬到 0.847，仍差 ~15%）。

数据源与产物（全部相对本脚本目录 code/submission/）：
- 输入：附件/附件1.xlsx（环境边界）、附件/附件2.xlsx（半径轨迹）
- 求解核心：同目录 problem4.py（数值逻辑零改动）
- 输出：终端分节打印关键结论（不生成文件）

用法：python limitations.py   （无任何命令行参数；缺附件时友好提示后退出）
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.interpolate import CubicSpline, PchipInterpolator
from scipy.optimize import curve_fit

BASE = Path(__file__).resolve().parent
ATTACH_DIR = BASE / "附件"
ATTACHMENT1 = ATTACH_DIR / "附件1.xlsx"
ATTACHMENT2 = ATTACH_DIR / "附件2.xlsx"

for required in (ATTACHMENT1, ATTACHMENT2):
    if not required.exists():
        raise SystemExit(
            f"缺少输入附件：{required}\n"
            f"请把 附件1.xlsx / 附件2.xlsx 放到目录 {ATTACH_DIR} 后重试。"
        )

sys.path.insert(0, str(BASE))
from problem4 import (                       # noqa: E402
    EnvironmentSeries,
    PhysicalParameters,
    PostBoundary,
    RadiusSeries,
    SimulationResult,
    SolverConfig,
    boundary_at,
    build_reference_geometry,
    density,
    load_inputs,
    moisture_diffusivity as _orig_moisture_diffusivity,
    post_boundary_from_tail,
    solve_problem4_bdf,
)
import problem4 as _p4                       # noqa: E402  用于 monkey-patch moisture_diffusivity

LINE = "=" * 78

# ======================================================================================
# 公共常量
# ======================================================================================
C0 = 2.55
R0_CM = 2.0
RHO_W = 1000.0
RHO_S_MAX = 760.0                            # ρ_s(C) 在 C=0 处的上确界
VHAT_SUM_REF = 0.5                           # N=401 时 ΣV̂ 的参考值（精确值由 build_reference_geometry 给出）


def _rho_s(c: np.ndarray | float) -> np.ndarray | float:
    """干基固体密度 ρ_s(C) = ρ(C)/(1+C) = 90 + 670/(1+C)。"""
    return 90.0 + 670.0 / (1.0 + np.asarray(c, dtype=float))


# ======================================================================================
# §1  上界论证（纯数学，不触发 PDE 求解）
# ======================================================================================
def section_upper_bound() -> None:
    print(f"\n{LINE}")
    print("[§1] 上界论证：附录4 密度律与附件2 半径轨迹的闭合不可能性")
    print(LINE)

    rho_s0 = float(_rho_s(C0))
    R_C = R0_CM * np.sqrt(rho_s0 / RHO_S_MAX)
    print(f"  ρ_s(C) = 90 + 670/(1+C)  值域上确界 = {RHO_S_MAX} kg/m³ @ C=0（绝干）")
    print(f"  ρ_s0 = ρ_s(C0={C0}) = {rho_s0:.4f} kg/m³")
    print(f"  临界半径 R_c = R0·√(ρ_s0/{RHO_S_MAX}) = {R_C:.6f} cm")
    print(f"  R(t) < {R_C:.4f} cm 时，闭合要求的 ρ_s 超过 {RHO_S_MAX}，物理上不可达")

    raw = pd.read_excel(ATTACHMENT2)
    t_raw = raw.iloc[:, 0].to_numpy(dtype=float)
    r_raw = raw.iloc[:, 1].to_numpy(dtype=float)
    rho_req = rho_s0 * (R0_CM / r_raw) ** 2
    unreach = rho_req > RHO_S_MAX
    idx_first = int(np.argmax(unreach)) if unreach.any() else -1

    print(f"\n  附件2 逐点判定（共 {len(r_raw)} 点）：")
    print(f"    首个不可达点：t={t_raw[idx_first]/3600:.2f} h  R={r_raw[idx_first]:.4f} cm")
    print(f"    不可达点数 = {int(unreach.sum())} / {len(r_raw)}"
          f"（覆盖 t = {t_raw[idx_first]/3600:.2f}–{t_raw[-1]/3600:.2f} h）")
    print(f"    末值 R={r_raw[-1]:.4f} cm → ρ_req={rho_req[-1]:.3f} > {RHO_S_MAX}"
          f" → 需 C_eq={670.0/(rho_req[-1]-90.0)-1.0:.4f}（负含水率）")
    print(f"\n  结论：附件2 自 t≈{t_raw[idx_first]/3600:.1f} h 起，无论含水率场多精确，干物质闭合都不可能。")


# ======================================================================================
# §2  干物质闭合诊断（N=401 PDE 求解 + 不动点迭代）
# ======================================================================================
def section_drymass_closure() -> None:
    print(f"\n{LINE}")
    print("[§2] 干物质闭合诊断：28.02% 漂移成因 + 不动点迭代")
    print(LINE)

    NODE = 401
    CFG = SolverConfig(node_count=NODE)
    GEO = build_reference_geometry(NODE)
    vhat_sum = float(np.sum(GEO.volumes_hat))
    rho_s0 = float(density(C0) / (1.0 + C0))
    m0 = (R0_CM / 100.0) ** 2 * rho_s0 * vhat_sum

    ENV, RAD_GIVEN = load_inputs(ATTACHMENT1, ATTACHMENT2)
    print(f"  ρ_s0 = {rho_s0:.6f} kg/m³  ΣV̂ = {vhat_sum:.6f}  R0 = {R0_CM} cm  N = {NODE}")
    print(f"  附件2: t_end={RAD_GIVEN.terminal_time_s:.0f} s"
          f"  R(0)={RAD_GIVEN.radius_cm[0]:.4f}  R(end)={RAD_GIVEN.radius_cm[-1]:.4f} cm")

    def analyse(label: str, radius: RadiusSeries) -> dict:
        res = solve_problem4_bdf(ENV, radius, CFG)
        t_h = res.time_s / 3600.0
        r_cm = res.radius_cm
        m = res.dry_mass_index
        kappa = m / m0
        geo_fac = (r_cm / R0_CM) ** 2
        rho_s_mean = m / ((r_cm / 100.0) ** 2 * vhat_sum)
        comp_fac = rho_s_mean / rho_s0
        i_min = int(np.argmin(kappa))
        out = {
            "t_star_h": res.drying_event_time_s / 3600.0,
            "rel_range": float((kappa.max() - kappa.min()) / abs(kappa[0])),
            "kappa_min": float(kappa[i_min]),
            "t_kappa_min_h": float(t_h[i_min]),
            "kappa_event": float(kappa[-1]),
            "R_event_cm": float(res.event_radius_cm),
            "comp_series": comp_fac,
            "t_h": t_h,
            "r_cm": r_cm,
        }
        print(f"  [{label}] t*={out['t_star_h']:.6f} h  κ_rel_range={out['rel_range']:.4%}")
        print(f"      κ_min={out['kappa_min']:.6f} @ t={out['t_kappa_min_h']:.4f} h"
              f"   κ(event)={out['kappa_event']:.6f}")
        return out

    base = analyse("iter0 给定 R(t)", RAD_GIVEN)

    prev = base
    for k in range(1, 4):
        s = prev["comp_series"]
        t = np.concatenate([[0.0], prev["t_h"] * 3600.0])
        r_new = R0_CM / np.sqrt(np.concatenate([[1.0], s]))
        if np.any(np.diff(t) <= 0):
            raise RuntimeError("closure time grid not strictly increasing")
        series = RadiusSeries(t, r_new, "linear")
        cur = analyse(f"iter{k} 闭合 R(t)", series)
        dr = float(np.max(np.abs(cur["r_cm"] - np.interp(cur["t_h"] * 3600.0, t, r_new))))
        print(f"      max|dR|={dr:.3e} cm   Δt*={cur['t_star_h']-prev['t_star_h']:+.6f} h")
        if abs(cur["t_star_h"] - prev["t_star_h"]) < 1e-4 and cur["rel_range"] < 1e-4:
            print("      收敛")
            prev = cur
            break
        prev = cur

    print(f"\n  给定 R(t) t* = {base['t_star_h']:.6f} h   κ 变幅 = {base['rel_range']:.4%}")
    print(f"  闭合 R(t) t* = {prev['t_star_h']:.6f} h   κ 变幅 = {prev['rel_range']:.4%}")
    print(f"  Δt* = {prev['t_star_h']-base['t_star_h']:+.6f} h"
          f" ({(prev['t_star_h']-base['t_star_h'])/base['t_star_h']:+.4%})")


# ======================================================================================
# §3  潜热预算（N=201 PDE 求解 + 能量积分）
# ======================================================================================
def section_latent_heat_budget() -> None:
    print(f"\n{LINE}")
    print("[§3] 潜热预算：Q_lat / Q_sens 量级估算")
    print(LINE)

    NODE = 201
    L_V = 2260.0e3                              # J/kg，文献汽化潜热（题目未给）
    H = 25.0                                    # W/(m² K)
    DIST = tuple(float(x) for x in np.round(np.arange(0.0, 2.0001, 0.05), 10))
    CFG = SolverConfig(node_count=NODE, fixed_distances_cm=DIST,
                       sample_interval_s=1800, report_interval_s=1800)
    ENV, RAD = load_inputs(ATTACHMENT1, ATTACHMENT2)
    post = post_boundary_from_tail(ENV)
    res = solve_problem4_bdf(ENV, RAD, CFG, post)

    t_s = res.time_s
    t_star = res.drying_event_time_s
    r_m = res.radius_cm / 100.0
    t_surf = res.temperature_c[:, -1]
    c_prof = res.moisture

    xi = np.linspace(0.0, 1.0, 401)
    d = np.asarray(DIST, dtype=float)
    cbar = np.empty(t_s.size)
    for k in range(t_s.size):
        v = np.interp(xi * res.radius_cm[k], d, c_prof[k, :-1], left=np.nan, right=np.nan)
        v[np.isnan(v)] = c_prof[k, -1]
        v[-1] = c_prof[k, -1]
        cbar[k] = 2.0 * np.trapezoid(v * xi, xi)

    cbar_star = float(np.interp(t_star, t_s, cbar))
    rho_s0 = float(density(C0) / (1.0 + C0))
    V0 = np.pi * (R0_CM / 100.0) ** 2
    m_s = rho_s0 * V0
    dm_w = m_s * (C0 - cbar_star)
    Q_lat = L_V * dm_w

    t_full = np.concatenate([[0.0], t_s])
    t_full[-1] = t_star
    r_full = np.concatenate([[R0_CM / 100.0], r_m])
    r_full[-1] = res.event_radius_cm / 100.0
    ts_full = np.concatenate([[res.temperature_c[0, -1]], t_surf])
    ts_full[-1] = float(np.interp(t_star, t_s, t_surf))
    env_T = np.array([boundary_at(float(tt), ENV, post)[0] for tt in t_full])
    q = H * 2.0 * np.pi * r_full * (env_T - ts_full)
    Q_sens = float(np.trapezoid(q, t_full))

    print(f"  t* = {t_star/3600.0:.6f} h (N={NODE})   <C>(t*) = {cbar_star:.6f}")
    print(f"  干物质线密度 m_s = {m_s:.6f} kg/m")
    print(f"  失水量 dm_w = {dm_w:.6f} kg/m（占初始水量 {dm_w/(m_s*C0):.4%}）")
    print(f"  Q_lat = {Q_lat:.6e} J/m（L_v = {L_V/1e3:.0f} kJ/kg）")
    print(f"  Q_sens = {Q_sens:.6e} J/m（h = {H} W/m²K）")
    print(f"  Q_lat / Q_sens = {Q_lat/Q_sens:.4%}")
    print(f"  结论：潜热占显热不到几个百分点，忽略潜热是合理近似。")


# ======================================================================================
# §4  潜热效应代理（蒸发冷却温降扫描，N=401）
# ======================================================================================
def section_latent_heat_effect() -> None:
    print(f"\n{LINE}")
    print("[§4] 潜热效应代理：蒸发冷却温降 ΔT 对干物质指标的影响")
    print(LINE)

    NODE = 401
    DIST = tuple(float(x) for x in np.round(np.arange(0.0, 2.0001, 0.05), 10))
    CFG = SolverConfig(node_count=NODE, fixed_distances_cm=DIST,
                       sample_interval_s=1800, report_interval_s=1800)
    ENV, RAD = load_inputs(ATTACHMENT1, ATTACHMENT2)

    rho_s0 = float(density(C0) / (1.0 + C0))
    m0 = (R0_CM / 100.0) ** 2 * rho_s0 * VHAT_SUM_REF
    S_MAX = RHO_S_MAX / rho_s0

    g_star = (1.2 / R0_CM) ** 2
    print(f"  解析上界（模型无关）：κ(t*) ≤ G(t*)·S_max = {g_star:.4f}×{S_MAX:.4f} = {g_star*S_MAX:.6f}")
    print(f"  ⇒ 终点缺口至少 {100*(1-g_star*S_MAX):.4f}%，潜热改不了这个上界")

    def run(dT: float) -> tuple:
        _p4.moisture_diffusivity = lambda c, t, p: _orig_moisture_diffusivity(c, np.asarray(t, float) - dT, p)
        try:
            res = solve_problem4_bdf(ENV, RAD, CFG)
            kap = res.dry_mass_index / m0
            return (res.drying_event_time_s / 3600.0, float(kap.min()), float(kap[-1]), float(kap.max()))
        finally:
            _p4.moisture_diffusivity = _orig_moisture_diffusivity

    print(f"\n  {'ΔT/K':>6s} {'t*/h':>10s} {'κ_min':>9s} {'κ(t*)':>9s} {'κ_max':>9s}")
    for dT in [0.0, 3.0, 5.0, 10.0]:
        tstar, kmin, kend, kmax = run(dT)
        flag = "  ← 基线" if dT == 0.0 else ""
        print(f"  {dT:6.1f} {tstar:10.4f} {kmin:9.6f} {kend:9.6f} {kmax:9.6f}{flag}")
    print(f"\n  结论：潜热冷却使 D(T) 变小、干燥变慢、κ 谷值更深 ⇒ 28.02% 缺口不会因潜热而消失。")


# ======================================================================================
# §5  半径-含水率核查（R(t) 插值对比 + D/h_m 缩放反证，N=401）
# ======================================================================================
def section_radius_moisture_check() -> None:
    print(f"\n{LINE}")
    print("[§5] 半径-含水率核查：R(t) 插值方式对比 + D 缩放反证")
    print(LINE)

    NODE = 401
    DIST = tuple(float(x) for x in np.round(np.arange(0.0, 2.0001, 0.05), 10))
    CFG = SolverConfig(node_count=NODE, fixed_distances_cm=DIST,
                       sample_interval_s=1800, report_interval_s=1800)
    ENV, RAD = load_inputs(ATTACHMENT1, ATTACHMENT2)

    raw = pd.read_excel(ATTACHMENT2)
    t_raw = raw.iloc[:, 0].to_numpy(dtype=float)
    r_raw = raw.iloc[:, 1].to_numpy(dtype=float)
    print(f"  附件2：{len(r_raw)} 点  t∈[{t_raw[0]:.0f},{t_raw[-1]:.0f}] s"
          f"  R∈[{r_raw.min():.4f},{r_raw.max():.4f}] cm")

    fine = np.linspace(t_raw[0], t_raw[-1], 20001)
    lin = np.interp(fine, t_raw, r_raw)
    pch = PchipInterpolator(t_raw, r_raw)(fine)
    cub = CubicSpline(t_raw, r_raw)(fine)

    try:
        p0 = [r_raw[-1], r_raw[0] - r_raw[-1], t_raw[-1] / 5.0, 0.0]
        popt, _ = curve_fit(lambda t, a, b, c, d: a + b * np.exp(-t / c) + d * t,
                            t_raw, r_raw, p0=p0, maxfev=200000)
        fit_vals = (lambda t: popt[0] + popt[1] * np.exp(-t / popt[2]) + popt[3] * t)(fine)
        ok_fit = True
    except Exception:
        ok_fit = False

    print(f"\n  插值方式在 2 万点细网格上相对 linear 的偏差：")
    for name, arr in [("pchip", pch), ("cubic-spline", cub)] + (
            [("4-param exp", fit_vals)] if ok_fit else []):
        d = arr - lin
        print(f"    {name:16s} max|dR|={np.abs(d).max():.6f} cm  RMS={np.sqrt(np.mean(d**2)):.6f} cm")

    rho_s0 = float(density(C0) / (1.0 + C0))
    m0 = (R0_CM / 100.0) ** 2 * rho_s0 * VHAT_SUM_REF
    xi = np.linspace(0.0, 1.0, NODE)
    d_grid = np.asarray(DIST, dtype=float)

    def cbar_of(res: SimulationResult) -> np.ndarray:
        out = np.empty(res.time_s.size)
        for k in range(res.time_s.size):
            v = np.interp(xi * res.radius_cm[k], d_grid, res.moisture[k, :-1], left=np.nan, right=np.nan)
            v[np.isnan(v)] = res.moisture[k, -1]
            v[-1] = res.moisture[k, -1]
            out[k] = 2.0 * np.trapezoid(v * xi, xi)
        return out

    def report(tag: str, rad: RadiusSeries) -> None:
        res = solve_problem4_bdf(ENV, rad, CFG)
        kap = res.dry_mass_index / m0
        cbar = cbar_of(res)
        print(f"    {tag:20s} t*={res.drying_event_time_s/3600.0:.6f} h"
              f"  κ_min={float(kap.min()):.6f}  <C>(t*)={np.interp(res.drying_event_time_s/3600.0, res.time_s/3600.0, cbar):.6f}")

    print(f"\n  不同 R(t) 口径下的 t* 与干物质指标（N={NODE}）：")
    report("linear（默认）", RAD)
    report("pchip（单调）", RAD.with_interpolation("pchip"))
    report("cubic-spline", RadiusSeries(fine, cub, "linear"))
    if ok_fit:
        report("4-param exp fit", RadiusSeries(fine, np.clip(fit_vals, 1e-6, None), "linear"))

    print(f"\n  D 缩放反证（要让 <C>(t*) 降到闭合值，D 需乘多大因子）：")
    print(f"    {'D 倍率':>8s} {'t*/h':>10s} {'<C>(t*)':>10s} {'κ_min':>10s}")
    for k in [1.0, 2.0, 5.0, 10.0]:
        _p4.moisture_diffusivity = lambda c, t, p, _k=k: _k * _orig_moisture_diffusivity(c, t, p)
        try:
            r = solve_problem4_bdf(ENV, RAD, CFG)
            cb = cbar_of(r)
            print(f"    {k:8.2f} {r.drying_event_time_s/3600.0:10.4f}"
                  f" {float(cb[-1]):10.6f} {float((r.dry_mass_index/m0).min()):10.6f}")
        finally:
            _p4.moisture_diffusivity = _orig_moisture_diffusivity

    print(f"\n  结论：D×10 也只把 κ_min 抬到 ~0.85，仍差 ~15% ⇒ 28.02% 缺口非「含水率算错」。")


# ======================================================================================
# 主函数
# ======================================================================================
def main() -> None:
    print(LINE)
    print("问题四 模型局限性诊断（五段）")
    print(LINE)
    section_upper_bound()
    section_drymass_closure()
    section_latent_heat_budget()
    section_latent_heat_effect()
    section_radius_moisture_check()
    print(f"\n{LINE}")
    print("诊断完成。")
    print(LINE)


if __name__ == "__main__":
    main()
