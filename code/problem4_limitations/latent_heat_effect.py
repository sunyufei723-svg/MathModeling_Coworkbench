"""局限性分析诊断脚本（已收入 code/problem4_limitations/）：研究「算上汽化潜热后 28.02% 会不会消失」。

物理链条（模型无关，只判方向）：
  汽化潜热 = 能量汇 → 物料降温 → D = 4.2e-4·exp(-0.30/C)·exp(-3850/T_K) 随 T 下降
  → 干燥变慢 → 同一时刻 C 更高 → 干基密度 ρ_s(C)=90+670/(1+C) 更低
  → 组成因子 S=⟨ρ_s⟩/ρ_s(C0) 更低 → κ=G·S 更低 → 谷值更深、变幅更大。
  而几何因子 G=(R/R0)^2 完全由附件2 给定的 R(t) 决定，潜热改不了它。

数值代理（清楚标注为代理）：给温度场整体减去一个「蒸发冷却温降 ΔT」，
  用真实的 D(T) 依赖让干燥变慢；ΔT=0 必须逐位复现基线（自检）。
  §二 的能量预算给出等效温降 4.5–5.4 K，这里扫 ΔT=0/3/5/10 K。

同时直接验证解析上界：κ(t*) ≤ G(t*)·S_max = 0.36 × 760/278.7324 = 0.9816，
  对任何 C≥0 场（含任何潜热模型产出的场）都成立 ⇒ 终点缺口至少 1.84%，永不闭合。

只读 import，不修改任何仓库文件；PYTHONDONTWRITEBYTECODE=1，无 __pycache__。
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]   # 仓库根（脚本在 code/problem4_limitations/）
# 让 stdout/stderr 用 UTF-8，避免 Windows 管道/重定向下 GBK 编码崩溃（脚本含 ⇒ κ ρ ⟨⟩ 等字符）
for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8")
    except (AttributeError, ValueError):
        pass
PKG = ROOT / "code" / "problem4_fvm_bdf"
sys.path.insert(0, str(PKG))

import solver_bdf as sb  # noqa: E402
from model import density  # noqa: E402
from run_and_verify import load_inputs  # noqa: E402
from solver_bdf import SolverConfig, solve_problem4_bdf  # noqa: E402

NODE = 401
C0 = 2.55
R0_CM = 2.0
VHAT_SUM = 0.5

DIST = tuple(float(x) for x in np.round(np.arange(0.0, 2.0001, 0.05), 10))
CFG = SolverConfig(node_count=NODE, fixed_distances_cm=DIST,
                   sample_interval_s=1800, report_interval_s=1800)
ENV, RAD = load_inputs(ROOT / "附件" / "附件1.xlsx", ROOT / "附件" / "附件2.xlsx")

rho_s0 = float(density(C0) / (1.0 + C0))          # 278.7324
m0 = (R0_CM / 100.0) ** 2 * rho_s0 * VHAT_SUM
S_MAX = 760.0 / rho_s0                             # 2.7266，C≡0 时的组成因子上界

# ------------------------------------------------------------------ 解析上界
print("=" * 78)
print("解析上界（模型无关，潜热改不了）:")
print(f"   rho_s0 = rho_s(C0=2.55) = {rho_s0:.4f} kg/m^3")
print(f"   rho_s(C) = 90 + 670/(1+C) 在 C>=0 上上确界 = 760 kg/m^3 (C=0)")
print(f"   S_max = 760/rho_s0 = {S_MAX:.6f}")
g_star = (1.2 / R0_CM) ** 2
print(f"   G(t*) = (1.2/2.0)^2 = {g_star:.4f}")
print(f"   => kappa(t*) <= G*S_max = {g_star*S_MAX:.6f}  ⇒ 终点缺口至少 {100*(1-g_star*S_MAX):.4f}%")

# ------------------------------------------------------------------ 潜热代理
orig_D = sb.moisture_diffusivity


def run(dT):
    """给温度场减去 dT（蒸发冷却），用真实 D(T) 让干燥变慢；dT=0 为基线自检。"""
    sb.moisture_diffusivity = lambda c, t: orig_D(c, np.asarray(t, float) - dT)
    try:
        res = solve_problem4_bdf(ENV, RAD, CFG)
        kap = res.dry_mass_index / m0
        ts = res.time_s / 3600.0
        kmin = float(kap.min())
        itrough = int(np.argmin(kap))
        kend = float(kap[-1])
        return (res.drying_event_time_s / 3600.0, kmin, ts[itrough], kend,
                100 * (1 - kmin), float(kap.max()))
    finally:
        sb.moisture_diffusivity = orig_D


print("=" * 78)
print("潜热代理（蒸发冷却温降 ΔT）对干物质指标的影响（N=401）:")
print(f"   {'ΔT/K':>6s} {'t*/h':>10s} {'κ_min':>9s} {'谷值t/h':>8s} "
      f"{'κ(t*)':>9s} {'κ_max':>9s} {'变幅%':>9s}")
for dT in [0.0, 3.0, 5.0, 10.0]:
    tstar, kmin, ttr, kend, rng, kmax = run(dT)
    flag = "  ← 基线自检" if dT == 0.0 else ""
    print(f"   {dT:6.1f} {tstar:10.4f} {kmin:9.6f} {ttr:8.1f} "
          f"{kend:9.6f} {kmax:9.6f} {rng:9.4f}{flag}")

print("=" * 78)
print("基线自检目标：t*=50.844229 h，κ_min=0.719829（应与归档逐位一致）")
