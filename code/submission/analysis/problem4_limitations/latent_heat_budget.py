"""局限性分析诊断脚本（已收入 code/problem4_limitations/）：量化「未引入汽化潜热源项」这一跨问共近似的量级。

思路（明确标注为量级估算，不作为答案）：
  失水量  dm_w = m_s * (C0 - <C>(t*))，m_s 由附录4 干基密度在 t=0 的体积积分给出；
  潜热总耗 Q_lat = L_v * dm_w，取文献值 L_v = 2260 kJ/kg；
  显热总入 Q_sens = int_0^{t*} h * 2*pi*R(t) * (T_env(t) - T_surf(t)) dt，
  其中 T_surf 取模拟表面温度、T_env 取附件1（4 h 后按末值恒定延拓，与主模型口径一致）。
  报告比值 Q_lat / Q_sens，用以判断「忽略潜热」对温度场的影响量级。
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

from environment import post_boundary_from_tail, boundary_at  # noqa: E402
from model import density  # noqa: E402
from run_and_verify import load_inputs  # noqa: E402
from solver_bdf import SolverConfig, solve_problem4_bdf  # noqa: E402

NODE = 201
L_V = 2260.0e3      # J/kg，文献汽化潜热（题目未给）
H = 25.0            # W/(m^2 K)
C0 = 2.55
R0_CM = 2.0
DIST = tuple(float(x) for x in np.round(np.arange(0.0, 2.0001, 0.05), 10))
CFG = SolverConfig(node_count=NODE, fixed_distances_cm=DIST,
                   sample_interval_s=1800, report_interval_s=1800)
ENV, RAD = load_inputs(ROOT / "附件" / "附件1.xlsx", ROOT / "附件" / "附件2.xlsx")
post = post_boundary_from_tail(ENV)
res = solve_problem4_bdf(ENV, RAD, CFG, post)

a1 = pd.read_excel(ROOT / "附件" / "附件1.xlsx")
print("附件1 列名:", list(a1.columns))
print(f"附件1 时间范围 {a1.iloc[0,0]:.0f}–{a1.iloc[-1,0]:.0f} s，"
      f"环境温度 {a1.iloc[:,1].min():.2f}–{a1.iloc[:,1].max():.2f} °C，"
      f"环境含水率 {a1.iloc[:,2].min():.4f}–{a1.iloc[:,2].max():.4f}")

t_s = res.time_s
t_star = res.drying_event_time_s
r_m = res.radius_cm / 100.0
t_surf = res.temperature_c[:, -1]                       # 末列 = 移动表面
c_prof = res.moisture

# 体积平均含水率（用固定位置剖面重建 xi 网格）
xi = np.linspace(0.0, 1.0, 401)
d = np.asarray(DIST, dtype=float)
cbar = np.empty(t_s.size)
for k in range(t_s.size):
    v = np.interp(xi * res.radius_cm[k], d, c_prof[k, :-1], left=np.nan, right=np.nan)
    v[np.isnan(v)] = c_prof[k, -1]
    v[-1] = c_prof[k, -1]
    cbar[k] = 2.0 * np.trapezoid(v * xi, xi)

# 事件时刻的 <C>（线性插到 t*）
cbar_star = float(np.interp(t_star, t_s, cbar))
rho_s0 = float(density(C0) / (1.0 + C0))
V0 = np.pi * (R0_CM / 100.0) ** 2                        # m^2 per m length
m_s = rho_s0 * V0                                        # kg per m length
dm_w = m_s * (C0 - cbar_star)
Q_lat = L_V * dm_w

# 显热输入：环境温度为附件1 分段线性 + 末值恒定延拓
t_full = np.concatenate([[0.0], t_s])
t_full[-1] = t_star
r_full = np.concatenate([[R0_CM / 100.0], r_m])
r_full[-1] = res.event_radius_cm / 100.0
ts_full = np.concatenate([[res.temperature_c[0, -1]], t_surf])
ts_full[-1] = float(np.interp(t_star, t_s, t_surf))
env_T = np.array([boundary_at(float(tt), ENV, post)[0] for tt in t_full])
q = H * 2.0 * np.pi * r_full * (env_T - ts_full)         # W per m length
Q_sens = float(np.trapezoid(q, t_full))

print("=" * 78)
print(f"t* = {t_star/3600.0:.6f} h (N={NODE})   <C>(t*) = {cbar_star:.6f}   <C>(0) = {C0}")
print(f"干物质线密度 m_s = {m_s:.6f} kg/m   （rho_s0 = {rho_s0:.4f} kg/m^3, V0 = {V0:.6e} m^2/m）")
print(f"失水量 dm_w = {dm_w:.6f} kg/m   （占初始水量 {dm_w/(m_s*C0):.4%}）")
print(f"潜热总耗 Q_lat = {Q_lat:.6e} J/m   （L_v = {L_V/1e3:.0f} kJ/kg，文献值，题目未给）")
print(f"显热总入 Q_sens = {Q_sens:.6e} J/m   （h = {H} W/m^2K，T_env 用附件1+末值延拓）")
print(f"比值 Q_lat / Q_sens = {Q_lat/Q_sens:.4%}")
print(f"平均显热功率 = {Q_sens/t_star:.4f} W/m   平均潜热功率 = {Q_lat/t_star:.4f} W/m")
print(f"环境温度均值 = {env_T.mean():.4f} °C   表面温度均值 = {ts_full.mean():.4f} °C")
print(f"表面温度范围 = {ts_full.min():.4f}–{ts_full.max():.4f} °C")
