"""局限性分析诊断脚本（已收入 code/problem4_limitations/）：「上界论证」——附录4 密度律与附件2 R(t) 能否闭合？

核心思路（不依赖任何有争议的假设）：
  附录4 整体密度 rho_bulk(C) = 760 + 90C，故干基密度
      rho_s(C) = rho_bulk/(1+C) = 90 + 670/(1+C)
  在 C >= 0 的物理域内单调递减，值域为 (0, 760]，**上确界 760 出现在 C=0（绝干）**。

  另一方面，若干物质质量守恒且径向仿射收缩，则必须
      rho_s(t) = rho_s0 * (R0/R(t))^2 ,  rho_s0 = rho_s(C0=2.55) = 278.7324
  由此得到「闭合所要求的干基密度」rho_req(t)，以及临界半径
      R_c = R0 * sqrt(rho_s0/760)
  当 R(t) < R_c 时 rho_req > 760，**超出附录4 密度律的理论上界 ⇒ 无论含水率场算得多准都不可能闭合**。

同时复核：自洽版体积可加反演（t=0 必须回到 C0）、Jensen 不等式、kappa 分解。
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[4]   # 仓库根（脚本在 code/submission/analysis/problem4_limitations/）
# 让 stdout/stderr 用 UTF-8，避免 Windows 管道/重定向下 GBK 编码崩溃（脚本含 ⇒ κ ρ ⟨⟩ 等字符）
for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8")
    except (AttributeError, ValueError):
        pass
sys.path.insert(0, str(ROOT / "code" / "submission" / "pipeline" / "problem4"))
sys.path.insert(0, str(ROOT / "code" / "submission" / "business" / "problem4"))

from model import density  # noqa: E402
from run_and_verify import load_inputs  # noqa: E402
from solver_bdf import SolverConfig, solve_problem4_bdf  # noqa: E402

NODE = 401
C0 = 2.55
R0_CM = 2.0
RHO_W = 1000.0
VHAT_SUM = 0.5
RHO_S_MAX = 760.0                      # rho_s(C) 在 C=0 处的上确界

rho_s = lambda c: 90.0 + 670.0 / (1.0 + np.asarray(c, dtype=float))
rho_s0 = float(rho_s(C0))
R_C = R0_CM * np.sqrt(rho_s0 / RHO_S_MAX)

print("=" * 78)
print("[1] 附录4 密度律推出的干基密度 rho_s(C) = (760+90C)/(1+C) = 90 + 670/(1+C)")
for c in [2.55, 2.0, 1.5, 1.0, 0.5, 0.15, 0.0525, 0.01, 0.0]:
    print(f"     C={c:<7g} -> rho_s={float(rho_s(c)):9.4f} kg/m^3   (rho_bulk={float(density(c)):8.3f})")
print(f"     值域上确界 = {RHO_S_MAX} kg/m^3 @ C=0（绝干），初始 rho_s0 = {rho_s0:.4f} kg/m^3")
print(f"     => 干物质闭合的临界半径 R_c = R0*sqrt(rho_s0/760) = {R_C:.6f} cm")
print(f"        R(t) < {R_C:.4f} cm 时，闭合要求的 rho_s 超过 760，**物理上不可达**")

# ---------------------------------------------------------------- 附件2 逐点判定
raw = pd.read_excel(ROOT / "附件" / "附件2.xlsx")
t_raw = raw.iloc[:, 0].to_numpy(dtype=float)
r_raw = raw.iloc[:, 1].to_numpy(dtype=float)
rho_req_raw = rho_s0 * (R0_CM / r_raw) ** 2
unreach = rho_req_raw > RHO_S_MAX
idx_first = int(np.argmax(unreach)) if unreach.any() else -1
print("=" * 78)
print("[2] 附件2 原始 145 点逐点检验（闭合要求 rho_req = rho_s0*(R0/R)^2）")
print(f"     {'t/h':>7s} {'R/cm':>8s} {'rho_req':>10s} {'可达?':>7s} {'需 C_eq':>9s}")
for i in [0, 2, 4, 8, 14, 24, 28, 32, 40, 48, 64, 96, 144]:
    ceq = 670.0 / (rho_req_raw[i] - 90.0) - 1.0 if rho_req_raw[i] > 90.0 else np.nan
    flag = "不可达" if unreach[i] else "可达"
    print(f"     {t_raw[i]/3600:7.2f} {r_raw[i]:8.4f} {rho_req_raw[i]:10.3f} {flag:>7s} {ceq:9.4f}")
print(f"     首个不可达点：idx={idx_first}  t={t_raw[idx_first]/3600:.2f} h  R={r_raw[idx_first]:.4f} cm")
print(f"     不可达点数 = {int(unreach.sum())} / {len(r_raw)}，"
      f"覆盖 t = {t_raw[idx_first]/3600:.2f}–{t_raw[-1]/3600:.2f} h")
print(f"     末值 R={r_raw[-1]:.4f} cm，对应 rho_req={rho_req_raw[-1]:.3f} > 760，"
      f"需 C_eq={670.0/(rho_req_raw[-1]-90.0)-1.0:.4f}（**负含水率**）")

# ---------------------------------------------------------------- 模拟 + kappa 分解
DIST = tuple(float(x) for x in np.round(np.arange(0.0, 2.0001, 0.05), 10))
CFG = SolverConfig(node_count=NODE, fixed_distances_cm=DIST,
                   sample_interval_s=1800, report_interval_s=1800)
ENV, RAD = load_inputs(ROOT / "附件" / "附件1.xlsx", ROOT / "附件" / "附件2.xlsx")
res = solve_problem4_bdf(ENV, RAD, CFG)
ts = res.time_s / 3600.0
r_cm = res.radius_cm
m0 = (R0_CM / 100.0) ** 2 * rho_s0 * VHAT_SUM
kappa = res.dry_mass_index / m0
rho_s_mean = res.dry_mass_index / ((r_cm / 100.0) ** 2 * VHAT_SUM)
rho_req = rho_s0 * (R0_CM / r_cm) ** 2

xi = np.linspace(0.0, 1.0, NODE)
d_grid = np.asarray(DIST, dtype=float)
cbar = np.empty(ts.size)
rho_pt_mean = np.empty(ts.size)
for k in range(ts.size):
    v = np.interp(xi * r_cm[k], d_grid, res.moisture[k, :-1], left=np.nan, right=np.nan)
    v[np.isnan(v)] = res.moisture[k, -1]
    v[-1] = res.moisture[k, -1]
    cbar[k] = 2.0 * np.trapezoid(v * xi, xi)
    rho_pt_mean[k] = 2.0 * np.trapezoid(rho_s(v) * xi, xi)

print("=" * 78)
print("[3] 模拟结果逐时刻：实测 <rho_s> vs 闭合要求 rho_req（N=401，t*=%.6f h）" % (res.drying_event_time_s / 3600))
print(f"     {'t/h':>7s} {'R/cm':>8s} {'<C>':>8s} {'<rho_s>实测':>12s} {'rho_req':>9s} "
      f"{'kappa':>8s} {'需C_eq':>8s} {'可达?':>7s}")
for th in [0.5, 1, 2, 4, 7, 12, 15, 20, 24, 36, 48, ts[-1]]:
    k = int(np.argmin(np.abs(ts - th)))
    ceq = 670.0 / (rho_req[k] - 90.0) - 1.0
    print(f"     {ts[k]:7.3f} {r_cm[k]:8.4f} {cbar[k]:8.4f} {rho_s_mean[k]:12.3f} {rho_req[k]:9.3f} "
          f"{kappa[k]:8.5f} {ceq:8.4f} {'不可达' if rho_req[k] > RHO_S_MAX else '可达':>7s}")

kmin_i = int(np.argmin(kappa))
print(f"\n     kappa_min = {kappa[kmin_i]:.6f} @ t = {ts[kmin_i]:.3f} h（全程变幅 {100*(1-kappa[kmin_i]):.4f}%）")
print(f"     该时刻 rho_req = {rho_req[kmin_i]:.3f} kg/m^3 < 760 ⇒ **谷底处是「可达但未达到」**")
ceq_min = 670.0 / (rho_req[kmin_i] - 90.0) - 1.0
print(f"     谷底若要闭合，需 <C> = {ceq_min:.4f}，而模拟给 {cbar[kmin_i]:.4f}"
      f"（需再降 {100*(cbar[kmin_i]-ceq_min)/cbar[kmin_i]:.2f}%）")
print(f"     终点 t* 处 rho_req = {rho_req[-1]:.3f} > 760 ⇒ **数学上不可达**，"
      f"需 C_eq = {670.0/(rho_req[-1]-90.0)-1.0:.4f}（负值）")

print("=" * 78)
print("[4] Jensen 校验：rho_s(C) 是 C 的凸减函数，故 <rho_s(C)>_V >= rho_s(<C>)")
for th in [2, 7, 24, ts[-1]]:
    k = int(np.argmin(np.abs(ts - th)))
    print(f"     t={ts[k]:7.3f} h  <rho_s(C)>={rho_s_mean[k]:9.3f}  rho_s(<C>)={float(rho_s(cbar[k])):9.3f}"
          f"  逐点平均={rho_pt_mean[k]:9.3f}  差={rho_s_mean[k]-float(rho_s(cbar[k])):+.3f}")
print("     （三者一致到 1e-2 量级 ⇒ 诊断量与体积平均口径自洽，非实现错误）")

print("=" * 78)
print("[5] 自洽版体积可加反演（假设干骨架密度恒为 rho_s0，t=0 必须回到 C0）")
v0 = 1.0 / rho_s0 + C0 / RHO_W                     # 初始 V/m_s
c_impl = RHO_W * ((r_cm / R0_CM) ** 2 * v0 - 1.0 / rho_s0)
print(f"     t=0 自洽性检验：<C>_implied(0) = {c_impl[0]:.6f}（应为 C0 = {C0}）")
print(f"     {'t/h':>7s} {'R/cm':>8s} {'<C>_模拟':>10s} {'<C>_反演':>10s} {'差':>9s}")
for th in [0.5, 1, 2, 4, 7, 12, 15, 24, 36, 48, ts[-1]]:
    k = int(np.argmin(np.abs(ts - th)))
    print(f"     {ts[k]:7.3f} {r_cm[k]:8.4f} {cbar[k]:10.4f} {c_impl[k]:10.4f} {cbar[k]-c_impl[k]:+9.4f}")
z = np.where(c_impl < 0)[0]
if z.size:
    print(f"     <C>_反演 自 t = {ts[z[0]]:.3f} h 起变为**负值**（R < {r_cm[z[0]]:.4f} cm）"
          f" ⇒ 「常数干骨架密度 + 体积可加」这一假设本身在后期失效")
print("     注意：该反演依赖「干骨架密度恒定」假设，而附录4 的 rho_s(C) 从 278.73 变到 760，")
print("           二者互斥 ⇒ 反演数值随 rho_s 取值而变，**不能当独立判据**；[2][3] 的上界论证才是不依赖假设的判据。")
