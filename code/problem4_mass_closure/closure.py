"""L5 干物质闭合分支 —— 正式、独立、可复现的问题四「替代情景」求解器。

背景
----
题设直接模型（`code/problem4_fvm_bdf`，主答案 N3201 t*=50.8245 h）把附件 2 的
半径轨迹 R(t) 当作**已知输入**，并用附录 4 的经验密度 ρ(C)=760+90C 计算物性。
这两条题给关系在数学上并不自洽：干基固体密度

    ρ_s(C) = ρ(C)/(1+C) = 90 + 670/(1+C)      [kg/m^3]

在 C>=0 上单调递减、上确界 760（C=0 绝干），而「均匀仿射收缩 + 干骨架质量守恒」
要求 ρ_s(t) = ρ_s0·(R0/R(t))^2。把二者联立，附件 2 自 t=19.5 h 起就跌破临界半径
R_c=R0·sqrt(ρ_s0/760)=1.211203 cm（需负含水率才能闭合）。其直接后果是干物质闭合
指标 κ(t)=m(t)/m0（m=R^2·Σ ρ_s(C)·Vhat）在全程有 28.02% 的相对变幅，κ_min=0.7198
出现在 t≈7 h。详见 discussion/limitations_fix_analysis_by_A.md §1.4。

本模块做什么
------------
把上述诊断推进为一个**正式的替代情景（L5）**：不再把 R(t) 当已知，而是**强制干物质
闭合**，让半径轨迹由实际的密度演化自洽决定。闭合条件 κ≡1 等价于

    R_{k+1}(t) = R0 / sqrt(S_k(t)),    S_k(t) = <ρ_s>_k(t) / ρ_s0

其中 <ρ_s>_k 是第 k 次求解得到的体积平均干基密度。这是一个不动点迭代：给定 R_k(t)
→ 解热湿耦合 PDE → 得 C(ξ,t)、ρ_s(C)、S_k(t) → 更新 R_{k+1}(t)。收敛时 κ≡1（干物质
精确守恒），临界时间从 50.84 h 推迟到约 60.73 h（N401）。

铁律
----
* 闭合分支**只是模型形式对照，绝不替换题设直接模型主答案 50.8245 h**（附件 2 是题给
  数据，闭合轨迹与它矛盾，只能作为「若强制质量守恒会怎样」的反事实上界）。
* **只读** import `code/problem4_fvm_bdf` 的稳定已提交 API，不修改其任何文件。
"""
from __future__ import annotations

import sys
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]   # 仓库根（本文件在 code/problem4_mass_closure/）
# 强制 UTF-8，避免 Windows 管道/重定向下 GBK 编码崩溃（本模块 print 含 κ ρ ⟨⟩ ⇒ 等字符）
for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8")
    except (AttributeError, ValueError):
        pass

_SOLVER_DIR = ROOT / "code" / "problem4_fvm_bdf"
if str(_SOLVER_DIR) not in sys.path:
    sys.path.insert(0, str(_SOLVER_DIR))

from fvm import build_reference_geometry                       # noqa: E402
from model import density                                      # noqa: E402
from radius import RadiusSeries                                # noqa: E402
from run_and_verify import load_inputs                         # noqa: E402
from solver_bdf import SimulationResult, SolverConfig, solve_problem4_bdf  # noqa: E402


# --------------------------------------------------------------------------- #
# 契约自检：agent_C 正在参数化 problem4_fvm_bdf，若其改动下列 API，本模块立刻显式报错，
# 而不是静默算错。见 requests/agent_A.md「协作知悉（@agent_C）」。
# --------------------------------------------------------------------------- #
_REQUIRED_CFG_FIELDS = {
    "node_count", "sample_interval_s", "relative_tolerance",
    "temperature_absolute_tolerance", "moisture_absolute_tolerance",
    "max_time_step_s", "initial_moisture", "model_form",
}
_REQUIRED_RESULT_FIELDS = {
    "time_s", "radius_cm", "dry_mass_index", "drying_event_time_s",
    "event_radius_cm", "max_moisture", "diagnostics",
}


def _contract_check() -> None:
    cfg_fields = set(getattr(SolverConfig, "__dataclass_fields__", {}))
    missing_cfg = _REQUIRED_CFG_FIELDS - cfg_fields
    if missing_cfg:
        raise RuntimeError(
            "problem4_fvm_bdf.SolverConfig 缺少字段（API 漂移？）："
            f"{sorted(missing_cfg)}；请对照 requests/agent_A.md 与 agent_C 协调"
        )
    res_fields = set(getattr(SimulationResult, "__dataclass_fields__", {}))
    missing_res = _REQUIRED_RESULT_FIELDS - res_fields
    if missing_res:
        raise RuntimeError(f"problem4_fvm_bdf.SimulationResult 缺少字段：{sorted(missing_res)}")
    for symbol in (solve_problem4_bdf, load_inputs, build_reference_geometry, density):
        if not callable(symbol):
            raise RuntimeError(f"problem4_fvm_bdf 符号 {symbol!r} 不可调用")


_contract_check()


# --------------------------------------------------------------------------- #
# 配置与结果数据类
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class ClosureConfig:
    """闭合分支求解配置；默认与题设直接模型主口径（B2）逐字段一致，仅节点数可变。"""

    node_count: int = 401
    sample_interval_s: int = 60
    relative_tolerance: float = 1.0e-8
    temperature_absolute_tolerance: float = 1.0e-8
    moisture_absolute_tolerance: float = 1.0e-10
    max_time_step_s: float = 30.0
    max_iterations: int = 12
    t_star_tol_h: float = 1.0e-4        # 相邻迭代 t* 变化收敛阈
    kappa_range_tol: float = 1.0e-4     # κ 相对变幅收敛阈（→ 干物质闭合）

    def solver_config(self) -> SolverConfig:
        """映射到 problem4_fvm_bdf 的 SolverConfig（物质坐标、调和平均、连续事件）。"""
        return SolverConfig(
            node_count=self.node_count,
            sample_interval_s=self.sample_interval_s,
            relative_tolerance=self.relative_tolerance,
            temperature_absolute_tolerance=self.temperature_absolute_tolerance,
            moisture_absolute_tolerance=self.moisture_absolute_tolerance,
            max_time_step_s=self.max_time_step_s,
            model_form="material",
        )


@dataclass
class ClosureState:
    """一次求解（给定某条 R(t) 轨迹）得到的干物质闭合诊断量。"""

    label: str
    t_star_h: float
    radius: RadiusSeries
    t_h: np.ndarray              # 采样时刻（不含 t=0）
    r_cm: np.ndarray             # 对应半径
    kappa: np.ndarray            # κ(t)=m(t)/m0（不含 t=0）
    comp_series: np.ndarray      # S(t)=<ρ_s>/ρ_s0（不含 t=0）
    kappa_min: float
    t_kappa_min_h: float
    kappa_event: float
    kappa_rel_range: float       # (max-min)/|κ[0]|，与 drymass_closure 诊断同口径
    kappa_rel_range_official: float  # 求解器自带（含 t=0），与论文 28.02% 同口径
    R_event_cm: float
    coverage_terminal_h: float   # 本次 R(t) 序列覆盖到的终端时刻（bootstrap 诊断）


@dataclass
class ClosureResult:
    """一次完整不动点迭代（给定模型 iter0 + 闭合迭代 iter1..K）的结果。"""

    node_count: int
    r0_cm: float
    rho_s0: float
    vhat_sum: float
    m0: float
    given: ClosureState                 # iter0：题设直接模型（附件 2 R(t)）
    iterations: list                    # ClosureState 列表：iter1..iterK
    closure: ClosureState               # 最终（收敛）态
    converged: bool
    n_iterations: int
    delta_t_star_h: float               # closure.t* − given.t*
    delta_t_star_rel: float             # 相对 given.t*


# --------------------------------------------------------------------------- #
# 核心求解
# --------------------------------------------------------------------------- #
def _solve_state(
    label: str,
    environment,
    radius: RadiusSeries,
    config: ClosureConfig,
    m0: float,
    rho_s0: float,
    vhat_sum: float,
) -> ClosureState:
    """用给定 R(t) 解一次 PDE，并算出 κ、S 等闭合诊断量。"""
    result: SimulationResult = solve_problem4_bdf(environment, radius, config.solver_config())
    t_h = result.time_s / 3600.0
    r_cm = result.radius_cm
    m = result.dry_mass_index                       # = R^2 · Σ ρ_s(C)·Vhat
    kappa = m / m0                                   # 干物质闭合偏差 κ=G·S
    rho_s_mean = m / ((r_cm / 100.0) ** 2 * vhat_sum)
    comp = rho_s_mean / rho_s0                       # S=<ρ_s>/ρ_s0
    i_min = int(np.argmin(kappa))
    return ClosureState(
        label=label,
        t_star_h=result.drying_event_time_s / 3600.0,
        radius=radius,
        t_h=t_h,
        r_cm=r_cm,
        kappa=kappa,
        comp_series=comp,
        kappa_min=float(kappa[i_min]),
        t_kappa_min_h=float(t_h[i_min]),
        kappa_event=float(kappa[-1]),
        kappa_rel_range=float((kappa.max() - kappa.min()) / abs(kappa[0])),
        kappa_rel_range_official=float(result.diagnostics.dry_mass_index_relative_range),
        R_event_cm=float(result.event_radius_cm),
        coverage_terminal_h=float(t_h[-1]),
    )


def _closure_update(state: ClosureState, r0_cm: float) -> RadiusSeries:
    """闭合更新 R_{k+1}(t)=R0/sqrt(S_k(t))；t=0 处 S=1 ⇒ R=R0。

    与 drymass_closure 诊断逐式一致（S=<ρ_s>/ρ_s0），以保证 N401 复现 60.7312 h。
    等价形式 R_{k+1}=r_k/sqrt(κ_k)（因 κ=G·S、G=(r/R0)^2），此处保留 R0/sqrt(S) 写法。
    """
    t = np.concatenate([[0.0], state.t_h * 3600.0])
    r_new = r0_cm / np.sqrt(np.concatenate([[1.0], state.comp_series]))
    if np.any(np.diff(t) <= 0.0):
        raise RuntimeError("closure time grid not strictly increasing")
    if np.any(r_new <= 0.0) or not np.isfinite(r_new).all():
        raise RuntimeError("closure radius became non-positive or non-finite")
    return RadiusSeries(t, r_new, "linear")


def run_closure(
    environment,
    given_radius: RadiusSeries,
    config: ClosureConfig | None = None,
    r0_cm: float | None = None,
    verbose: bool = True,
) -> ClosureResult:
    """执行完整的干物质闭合不动点迭代。

    参数
    ----
    environment : problem4_fvm_bdf.EnvironmentSeries（附件 1）
    given_radius: problem4_fvm_bdf.RadiusSeries（附件 2，题设直接模型的 R(t)）
    config      : ClosureConfig（节点数、容差、迭代/收敛阈）
    r0_cm       : 初始半径，默认取 given_radius.radius_cm[0]（附件 2 首值，应=2.0）
    """
    config = config or ClosureConfig()
    node = config.node_count
    geometry = build_reference_geometry(node)
    vhat_sum = float(np.sum(geometry.volumes_hat))
    c0 = config.solver_config().initial_moisture
    rho_s0 = float(density(c0) / (1.0 + c0))         # = 90+670/(1+C0) = 278.7324
    if r0_cm is None:
        r0_cm = float(given_radius.radius_cm[0])
    m0 = (r0_cm / 100.0) ** 2 * rho_s0 * vhat_sum    # 初始干物质指数

    if verbose:
        print(f"[N={node}] ρ_s0={rho_s0:.6f} kg/m^3 (C0={c0})  ΣVhat={vhat_sum:.6f}  "
              f"R0={r0_cm:.4f} cm  m0={m0:.6e}", flush=True)

    given = _solve_state("iter0 given R(t)", environment, given_radius, config, m0, rho_s0, vhat_sum)
    if verbose:
        print(f"[N={node}] iter0 given : t*={given.t_star_h:.6f} h  "
              f"κ_range(official)={given.kappa_rel_range_official:.4%}  κ_min={given.kappa_min:.6f}",
              flush=True)

    states: list[ClosureState] = []
    prev = given
    converged = False
    for k in range(1, config.max_iterations + 1):
        series = _closure_update(prev, r0_cm)
        cur = _solve_state(f"iter{k} closure R(t)", environment, series, config, m0, rho_s0, vhat_sum)
        states.append(cur)
        dt = cur.t_star_h - prev.t_star_h
        if verbose:
            print(f"[N={node}] iter{k} closure: t*={cur.t_star_h:.6f} h  "
                  f"κ_range={cur.kappa_rel_range:.4%}  κ_min={cur.kappa_min:.6f}  "
                  f"Δt*={dt:+.6f} h  coverage→{cur.coverage_terminal_h:.4f} h", flush=True)
        if abs(dt) < config.t_star_tol_h and cur.kappa_rel_range < config.kappa_range_tol:
            converged = True
            prev = cur
            break
        prev = cur

    closure = prev
    return ClosureResult(
        node_count=node,
        r0_cm=r0_cm,
        rho_s0=rho_s0,
        vhat_sum=vhat_sum,
        m0=m0,
        given=given,
        iterations=states,
        closure=closure,
        converged=converged,
        n_iterations=len(states),
        delta_t_star_h=closure.t_star_h - given.t_star_h,
        delta_t_star_rel=(closure.t_star_h - given.t_star_h) / given.t_star_h,
    )
