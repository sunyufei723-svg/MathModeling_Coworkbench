"""局限性分析诊断脚本（已收入 code/problem4_limitations/）：核查队员对 Q4「28.02% 干物质漂移」的两个质疑。

质疑一：附件2 的 R(t) 是离散点，需要自己拟合曲线——会不会拟合过程有问题？
  → 打印附件2 全部原始数据（点数/间隔/端点）；
  → 比较代码默认的 linear 插值与单调 PCHIP 在细网格上的最大偏差；
  → 用 pchip 重跑 t*（N=401），与 linear 的 t* 和 kappa_min 对比；
  → 再试两种「平滑拟合」（三次样条 / 4 参数指数衰减最小二乘），看 R(t) 与 t* 的散布，
    以此判断 28.02% 的缺口是否可能来自拟合方式。

质疑二：会不会是含水率算错了？
  → 由附件2 的 R(t) 经体积可加性反演「隐含平均含水率」，与模拟值对照（**该反演前提自相矛盾，已被 upper_bound_proof.py 上界论证取代，仅作探索记录**）；
  → 关键新检验：要让模拟的 <C>(t) 匹配 R(t) 隐含的 <C>(t)，扩散系数 D 需要乘多大的因子 k？
    （运行时替换 solver 模块名空间里的 moisture_diffusivity，不修改任何仓库文件）
  → 同时试 h_m 放大倍数，判断哪个参数更可能是「算错」的入口。
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.interpolate import CubicSpline, PchipInterpolator
from scipy.optimize import curve_fit

ROOT = Path(__file__).resolve().parents[4]   # 仓库根（脚本在 code/submission/analysis/problem4_limitations/）
# 让 stdout/stderr 用 UTF-8，避免 Windows 管道/重定向下 GBK 编码崩溃（脚本含 ⇒ κ ρ ⟨⟩ 等字符）
for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8")
    except (AttributeError, ValueError):
        pass
PKG = ROOT / "code" / "submission" / "business" / "problem4"
sys.path.insert(0, str(PKG))
sys.path.insert(0, str(ROOT / "code" / "submission" / "pipeline" / "problem4"))

import solver_bdf as sb  # noqa: E402
from model import density  # noqa: E402
from radius import RadiusSeries  # noqa: E402
from run_and_verify import load_inputs  # noqa: E402
from solver_bdf import SolverConfig, solve_problem4_bdf  # noqa: E402

NODE = 401
C0 = 2.55
R0_CM = 2.0
RHO_S = 760.0
RHO_W = 1000.0
VHAT_SUM = 0.5

# ---------------------------------------------------------------- 附件2 原始数据
raw = pd.read_excel(ROOT / "附件" / "附件2.xlsx")
print("=" * 78)
print("附件2 列名:", list(raw.columns), " 行数:", len(raw))
t_raw = raw.iloc[:, 0].to_numpy(dtype=float)
r_raw = raw.iloc[:, 1].to_numpy(dtype=float)
print(f"时间范围 {t_raw[0]:.1f}–{t_raw[-1]:.1f} s = {t_raw[-1]/3600:.4f} h")
print(f"半径范围 {r_raw.min():.4f}–{r_raw.max():.4f} cm")
dt = np.diff(t_raw)
print(f"时间间隔: min={dt.min():.1f} s  max={dt.max():.1f} s  唯一值数={len(np.unique(np.round(dt,6)))}")
print(f"前 12 个间隔(s): {np.round(dt[:12],1).tolist()}")
print("原始数据（前 15 行 / 后 8 行）:")
for i in list(range(min(15, len(raw)))) + list(range(max(0, len(raw) - 8), len(raw))):
    print(f"   idx={i:4d}  t={t_raw[i]:10.1f}s ({t_raw[i]/3600:7.3f}h)  R={r_raw[i]:.4f} cm")
dr = np.abs(np.diff(r_raw))
print(f"半径单步变化: max={dr.max():.4f} cm  mean={dr.mean():.6f} cm  非单调步数={int((np.diff(r_raw)>0).sum())}")

# ---------------------------------------------------------------- 插值方式对比
fine = np.linspace(t_raw[0], t_raw[-1], 20001)
lin = np.interp(fine, t_raw, r_raw)
pch = PchipInterpolator(t_raw, r_raw)(fine)
cub = CubicSpline(t_raw, r_raw)(fine)


def expo(t, a, b, c, d):
    return a + b * np.exp(-t / c) + d * t


try:
    p0 = [r_raw[-1], r_raw[0] - r_raw[-1], t_raw[-1] / 5.0, 0.0]
    popt, _ = curve_fit(expo, t_raw, r_raw, p0=p0, maxfev=200000)
    fit = expo(fine, *popt)
    fit_res = np.sqrt(np.mean((expo(t_raw, *popt) - r_raw) ** 2))
    ok_fit = True
except Exception as exc:  # noqa: BLE001
    fit, fit_res, ok_fit, popt = lin, np.nan, False, None
    print("指数拟合失败:", exc)

print("=" * 78)
print("插值/拟合方式在 2 万点细网格上相对 linear 的偏差 (cm):")
for name, arr in [("pchip", pch), ("cubic-spline", cub), ("4-param exp fit", fit)]:
    d = arr - lin
    print(f"   {name:16s} max|dR|={np.abs(d).max():.6f}  RMS={np.sqrt(np.mean(d**2)):.6f}"
          f"  在 t*=183000s 处 dR={np.interp(183000.0, fine, d):+.6f}")
if ok_fit:
    print(f"   4 参数指数拟合对原始点的 RMS 残差 = {fit_res:.6f} cm，参数 = {np.round(popt,6).tolist()}")

# ---------------------------------------------------------------- 用不同 R(t) 重跑 t*
DIST = tuple(float(x) for x in np.round(np.arange(0.0, 2.0001, 0.05), 10))
CFG = SolverConfig(node_count=NODE, fixed_distances_cm=DIST,
                   sample_interval_s=1800, report_interval_s=1800)
ENV, RAD = load_inputs(ROOT / "附件" / "附件1.xlsx", ROOT / "附件" / "附件2.xlsx")
rho_s0 = float(density(C0) / (1.0 + C0))
m0 = (R0_CM / 100.0) ** 2 * rho_s0 * VHAT_SUM

xi = np.linspace(0.0, 1.0, NODE)
d_grid = np.asarray(DIST, dtype=float)


def cbar_of(res):
    out = np.empty(res.time_s.size)
    for k in range(res.time_s.size):
        v = np.interp(xi * res.radius_cm[k], d_grid, res.moisture[k, :-1], left=np.nan, right=np.nan)
        v[np.isnan(v)] = res.moisture[k, -1]
        v[-1] = res.moisture[k, -1]
        out[k] = 2.0 * np.trapezoid(v * xi, xi)
    return out


def report(tag, rad):
    res = solve_problem4_bdf(ENV, rad, CFG)
    ts = res.time_s / 3600.0
    kap = res.dry_mass_index / m0
    kmin = float(kap.min())
    cbar = cbar_of(res)
    c_impl = ((res.radius_cm / R0_CM) ** 2 - 1.0 / RHO_S) * RHO_W / 1.0
    c_impl = ((res.radius_cm / R0_CM) ** 2 * (1.0 / rho_s0) - 1.0 / RHO_S) * RHO_W
    print(f"   {tag:20s} t*={res.drying_event_time_s/3600.0:.6f} h  R(t*)={res.event_radius_cm:.4f} cm  "
          f"kappa_min={kmin:.6f}@{ts[int(np.argmin(kap))]:.1f}h  变幅={100*(1-kmin):.4f}%  "
          f"<C>(t*)={np.interp(res.drying_event_time_s/3600.0, ts, cbar):.6f}")
    return res, ts, cbar, kmin


print("=" * 78)
print("不同 R(t) 口径下的 t* 与干物质指标（N=401，其余参数不变）:")
res_lin, ts_lin, cbar_lin, kmin_lin = report("linear (代码默认)", RAD)
report("pchip (单调)", RAD.with_interpolation("pchip"))
report("cubic-spline", RadiusSeries(t_raw, r_raw, "pchip") if False else
       RadiusSeries(fine, cub, "linear"))
if ok_fit:
    report("4-param exp fit", RadiusSeries(fine, np.clip(fit, 1e-6, None), "linear"))

# ---------------------------------------------------------------- 质疑二：含水率是否算错
# ⚠️ 下面「R(t) 体积可加反演 <C>」对照已被 upper_bound_proof.py 的 [2][3] 上界论证取代：该反演
#    假设干骨架密度恒定，与附录4 ρ_s(C)（278.73→760）互斥，不能当独立判据（详见 limitations
#    _fix_analysis_by_A.md §1.4 更正）。本段保留作答「质疑二」的探索记录；真正的判据是上界论证
#    + 下面的 D/h_m 缩放反证（即便 D×10 也只把 κ_min 抬到 0.847，仍差约 15%，故非「含水率算错」）。
print("=" * 78)
print("模拟 <C> 与「由 R(t) 反演的隐含 <C>」对照（体积可加，rho_s=760, rho_w=1000）:")
c_impl_lin = ((res_lin.radius_cm / R0_CM) ** 2 * (1.0 / rho_s0) - 1.0 / RHO_S) * RHO_W
print(f"   {'t/h':>7s} {'R/cm':>8s} {'<C>_模拟':>10s} {'<C>_反演':>10s} {'差':>9s}")
for th in [0.5, 1.0, 2.0, 4.0, 7.0, 12.0, 24.0, 48.0, ts_lin[-1]]:
    k = int(np.argmin(np.abs(ts_lin - th)))
    print(f"   {ts_lin[k]:7.3f} {res_lin.radius_cm[k]:8.4f} {cbar_lin[k]:10.4f} "
          f"{c_impl_lin[k]:10.4f} {cbar_lin[k]-c_impl_lin[k]:+9.4f}")

# D 缩放因子标定：要让 t* 时刻的 <C> 落到反演值，D 需要乘多少？
orig_D = sb.moisture_diffusivity
target = float(np.interp(ts_lin[-1], ts_lin, c_impl_lin))
print(f"\n目标：把 <C>(t*) 从 {cbar_lin[-1]:.6f} 压到反演值 {target:.6f}（即让干物质在终点闭合）")


def try_scale(k):
    sb.moisture_diffusivity = lambda c, t: k * orig_D(c, t)
    try:
        r = solve_problem4_bdf(ENV, RAD, CFG)
        cb = cbar_of(r)
        return r.drying_event_time_s / 3600.0, float(cb[-1]), float((r.dry_mass_index / m0).min())
    finally:
        sb.moisture_diffusivity = orig_D


print(f"   {'D 倍率 k':>10s} {'t*/h':>10s} {'<C>(t*)':>10s} {'kappa_min':>10s}")
for k in [1.0, 1.5, 2.0, 3.0, 5.0, 10.0]:
    tstar, cbend, km = try_scale(k)
    print(f"   {k:10.2f} {tstar:10.4f} {cbend:10.6f} {km:10.6f}")

# h_m 缩放
orig_cfg_hm = CFG.mass_transfer_m_s
print("\n对照：放大表面传质系数 h_m（其余不变）")
print(f"   {'h_m 倍率':>10s} {'t*/h':>10s} {'<C>(t*)':>10s} {'kappa_min':>10s}")
for k in [1.0, 2.0, 5.0, 20.0]:
    cfg = SolverConfig(node_count=NODE, fixed_distances_cm=DIST, sample_interval_s=1800,
                       report_interval_s=1800, mass_transfer_m_s=orig_cfg_hm * k)
    r = solve_problem4_bdf(ENV, RAD, cfg)
    cb = cbar_of(r)
    print(f"   {k:10.2f} {r.drying_event_time_s/3600.0:10.4f} {float(cb[-1]):10.6f} "
          f"{float((r.dry_mass_index/m0).min()):10.6f}")

print("=" * 78)
print("参考：D 在典型状态点的数值 (m^2/s)")
for c, t in [(2.55, 28.0), (2.55, 50.0), (1.0, 50.0), (0.5, 50.0), (0.15, 50.0), (0.0525, 50.0)]:
    print(f"   C={c:<7g} T={t:<5g}C -> D={float(orig_D(c, t)):.6e}")
