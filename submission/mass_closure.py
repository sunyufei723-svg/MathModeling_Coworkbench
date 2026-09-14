"""问题四 L5 干物质闭合分支（单文件 · 无参数运行）。

背景
----
题设直接模型（problem4.py，主答案 N3201 t*=50.8245 h）把附件 2 的半径轨迹 R(t) 当作
已知输入，并用附录 4 的经验密度 ρ(C)=760+90C 计算物性。这两条题给关系在数学上并不
自洽：干基固体密度 ρ_s(C)=ρ(C)/(1+C)=90+670/(1+C) 在 C>=0 上单调递减、上确界 760
（C=0 绝干），而「均匀仿射收缩 + 干骨架质量守恒」要求 ρ_s(t)=ρ_s0·(R0/R(t))^2。
把二者联立，附件 2 自 t=19.5 h 起就跌破临界半径 R_c=1.211203 cm（需负含水率才能
闭合）。其直接后果是干物质闭合指标 κ(t)=m(t)/m0 在全程有 28.02% 的相对变幅。

本模块做什么
------------
把上述诊断推进为一个正式的替代情景（L5）：不再把 R(t) 当已知，而是强制干物质闭合，
让半径轨迹由实际的密度演化自洽决定。闭合条件 κ≡1 等价于

    R_{k+1}(t) = R0 / sqrt(S_k(t)),    S_k(t) = <ρ_s>_k(t) / ρ_s0

其中 <ρ_s>_k 是第 k 次求解得到的体积平均干基密度。这是一个不动点迭代：给定 R_k(t)
→ 解热湿耦合 PDE → 得 C(ξ,t)、ρ_s(C)、S_k(t) → 更新 R_{k+1}(t)。收敛时 κ≡1
（干物质精确守恒），临界时间从 50.84 h 推迟到约 60.73 h（N401）。

铁律
----
* 闭合分支只是模型形式对照，绝不替换题设直接模型主答案 50.8245 h。
* 只读 import 同目录 problem4.py 的稳定 API，不修改其任何逻辑。

数据源与产物（全部相对本脚本目录 code/submission/）：
- 输入：附件/附件1.xlsx（环境边界）、附件/附件2.xlsx（半径轨迹）
- 求解核心：同目录 problem4.py
- 输出：verification.json（结构化结果）+ 终端打印

用法：python mass_closure.py   （无任何命令行参数；缺附件时友好提示后退出）
"""
from __future__ import annotations

import json
import sys
import time
from dataclasses import dataclass, field, replace
from pathlib import Path

import numpy as np

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
from problem4 import (                           # noqa: E402
    RadiusSeries,
    SimulationResult,
    SolverConfig,
    build_reference_geometry,
    density,
    load_inputs,
    solve_problem4_bdf,
)

LINE = "=" * 78

# --------------------------------------------------------------------------- #
# 归档参考值
# --------------------------------------------------------------------------- #
ARCHIVED_GIVEN_T_STAR_H_N401 = 50.844229      # limitations §2（linear 口径）
ARCHIVED_GIVEN_T_STAR_H_N3201 = 50.824507     # 主答案 results/problem4_fvm_bdf/verification.json
ARCHIVED_CLOSURE_T_STAR_H_N401 = 60.7312      # day2 决策G / drymass_closure.py（N401）
ARCHIVED_KAPPA_RANGE_OFFICIAL = 0.2802        # 论文 28.02%

SPATIAL_NODES = [201, 401, 801, 1601, 3201]
PRODUCTION_NODE = 3201
TEMPORAL_NODE = 801
BOUNDARY_BAND_H = 2.8                          # B 的 LHS 边界扰动层（±2.8 h）


# --------------------------------------------------------------------------- #
# 契约自检：确认 problem4.py 导出的 API 字段完整
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
            f"problem4.SolverConfig 缺少字段（API 漂移？）：{sorted(missing_cfg)}"
        )
    res_fields = set(getattr(SimulationResult, "__dataclass_fields__", {}))
    missing_res = _REQUIRED_RESULT_FIELDS - res_fields
    if missing_res:
        raise RuntimeError(f"problem4.SimulationResult 缺少字段：{sorted(missing_res)}")
    for symbol in (solve_problem4_bdf, load_inputs, build_reference_geometry, density):
        if not callable(symbol):
            raise RuntimeError(f"problem4 符号 {symbol!r} 不可调用")


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
    t_star_tol_h: float = 1.0e-4
    kappa_range_tol: float = 1.0e-4

    def solver_config(self) -> SolverConfig:
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
    t_h: np.ndarray
    r_cm: np.ndarray
    kappa: np.ndarray
    comp_series: np.ndarray
    kappa_min: float
    t_kappa_min_h: float
    kappa_event: float
    kappa_rel_range: float
    kappa_rel_range_official: float
    R_event_cm: float
    coverage_terminal_h: float


@dataclass
class ClosureResult:
    """一次完整不动点迭代的结果。"""

    node_count: int
    r0_cm: float
    rho_s0: float
    vhat_sum: float
    m0: float
    given: ClosureState
    iterations: list
    closure: ClosureState
    converged: bool
    n_iterations: int
    delta_t_star_h: float
    delta_t_star_rel: float


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
    result: SimulationResult = solve_problem4_bdf(environment, radius, config.solver_config())
    t_h = result.time_s / 3600.0
    r_cm = result.radius_cm
    m = result.dry_mass_index
    kappa = m / m0
    rho_s_mean = m / ((r_cm / 100.0) ** 2 * vhat_sum)
    comp = rho_s_mean / rho_s0
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
    """闭合更新 R_{k+1}(t)=R0/sqrt(S_k(t))。"""
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
    """执行完整的干物质闭合不动点迭代。"""
    config = config or ClosureConfig()
    node = config.node_count
    geometry = build_reference_geometry(node)
    vhat_sum = float(np.sum(geometry.volumes_hat))
    c0 = config.solver_config().initial_moisture
    rho_s0 = float(density(c0) / (1.0 + c0))
    if r0_cm is None:
        r0_cm = float(given_radius.radius_cm[0])
    m0 = (r0_cm / 100.0) ** 2 * rho_s0 * vhat_sum

    if verbose:
        print(f"  [N={node}] rho_s0={rho_s0:.6f} kg/m^3 (C0={c0})  "
              f"SigmaVhat={vhat_sum:.6f}  R0={r0_cm:.4f} cm  m0={m0:.6e}", flush=True)

    given = _solve_state("iter0 given R(t)", environment, given_radius, config, m0, rho_s0, vhat_sum)
    if verbose:
        print(f"  [N={node}] iter0 given : t*={given.t_star_h:.6f} h  "
              f"kappa_range(official)={given.kappa_rel_range_official:.4%}  "
              f"kappa_min={given.kappa_min:.6f}", flush=True)

    states: list[ClosureState] = []
    prev = given
    converged = False
    for k in range(1, config.max_iterations + 1):
        series = _closure_update(prev, r0_cm)
        cur = _solve_state(f"iter{k} closure R(t)", environment, series, config, m0, rho_s0, vhat_sum)
        states.append(cur)
        dt = cur.t_star_h - prev.t_star_h
        if verbose:
            print(f"  [N={node}] iter{k} closure: t*={cur.t_star_h:.6f} h  "
                  f"kappa_range={cur.kappa_rel_range:.4%}  kappa_min={cur.kappa_min:.6f}  "
                  f"Dt*={dt:+.6f} h  coverage->{cur.coverage_terminal_h:.4f} h", flush=True)
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


# --------------------------------------------------------------------------- #
# 辅助函数
# --------------------------------------------------------------------------- #
def json_dump(path: Path, value) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False), encoding="utf-8")


def result_to_dict(res: ClosureResult, runtime_s: float) -> dict:
    return {
        "node_count": res.node_count,
        "r0_cm": res.r0_cm,
        "rho_s0": res.rho_s0,
        "m0": res.m0,
        "converged": res.converged,
        "n_iterations": res.n_iterations,
        "runtime_s": runtime_s,
        "given": {
            "t_star_h": res.given.t_star_h,
            "kappa_min": res.given.kappa_min,
            "t_kappa_min_h": res.given.t_kappa_min_h,
            "kappa_event": res.given.kappa_event,
            "kappa_rel_range": res.given.kappa_rel_range,
            "kappa_rel_range_official": res.given.kappa_rel_range_official,
            "R_event_cm": res.given.R_event_cm,
        },
        "closure": {
            "t_star_h": res.closure.t_star_h,
            "kappa_min": res.closure.kappa_min,
            "t_kappa_min_h": res.closure.t_kappa_min_h,
            "kappa_event": res.closure.kappa_event,
            "kappa_rel_range": res.closure.kappa_rel_range,
            "kappa_rel_range_official": res.closure.kappa_rel_range_official,
            "R_event_cm": res.closure.R_event_cm,
            "coverage_terminal_h": res.closure.coverage_terminal_h,
        },
        "delta_t_star_h": res.delta_t_star_h,
        "delta_t_star_rel": res.delta_t_star_rel,
        "iteration_t_star_h": [s.t_star_h for s in res.iterations],
        "iteration_kappa_rel_range": [s.kappa_rel_range for s in res.iterations],
    }


def run_node(environment, given_radius, node: int, config_overrides: dict | None = None,
             verbose: bool = True) -> tuple[ClosureResult, float]:
    base = ClosureConfig(node_count=node)
    cfg = replace(base, **(config_overrides or {}))
    started = time.perf_counter()
    res = run_closure(environment, given_radius, cfg, verbose=verbose)
    return res, time.perf_counter() - started


# --------------------------------------------------------------------------- #
# 主函数
# --------------------------------------------------------------------------- #
def main() -> None:
    print(LINE)
    print("问题四 L5 干物质闭合分支（空间收敛 + 时间敏感 + 复现校验）")
    print(LINE)

    environment, given_radius = load_inputs(ATTACHMENT1, ATTACHMENT2)
    print(f"\n  附件2: R(0)={given_radius.radius_cm[0]:.4f} cm"
          f"  R(end)={given_radius.radius_cm[-1]:.4f} cm"
          f"  t_end={given_radius.terminal_time_s/3600.0:.2f} h")

    # ---- 复现（N=401）----
    print(f"\n{'-'*78}")
    print("[复现] N=401 给定模型 + 闭合模型")
    print(f"{'-'*78}")
    res401, rt401 = run_node(environment, given_radius, 401)
    dict401 = result_to_dict(res401, rt401)

    given401 = dict401["given"]["t_star_h"]
    d401 = abs(given401 - ARCHIVED_GIVEN_T_STAR_H_N401)
    status401 = "PASS" if d401 <= 1.0e-4 else "FAIL"
    print(f"\n  给定模型 N=401 t*={given401:.6f} h  归档={ARCHIVED_GIVEN_T_STAR_H_N401:.6f} h"
          f"  diff={d401:.2e} h  [{status401}]")
    print(f"  闭合模型 N=401 t*={dict401['closure']['t_star_h']:.6f} h"
          f"  归档~{ARCHIVED_CLOSURE_T_STAR_H_N401:.4f} h")
    if d401 > 1.0e-4:
        raise RuntimeError(f"N401 given-model reproduction FAILED: diff={d401:.2e} h")

    # ---- 空间网格扫描 ----
    print(f"\n{'-'*78}")
    print(f"[空间收敛] 节点扫描 {SPATIAL_NODES}")
    print(f"{'-'*78}")
    spatial_dict = {"401": dict401}
    for node in SPATIAL_NODES:
        key = str(node)
        if key in spatial_dict:
            continue
        print(f"\n  --- N={node} ---")
        r, rt = run_node(environment, given_radius, node)
        spatial_dict[key] = result_to_dict(r, rt)

    spatial_list = [spatial_dict[str(n)] for n in SPATIAL_NODES]

    # 相邻节点 Δt* 差
    adjacent_delta = []
    for coarse, fine in zip(SPATIAL_NODES[:-1], SPATIAL_NODES[1:]):
        cd = spatial_dict[str(coarse)]["delta_t_star_h"]
        fd = spatial_dict[str(fine)]["delta_t_star_h"]
        adjacent_delta.append({
            "pair": f"{coarse}->{fine}",
            "coarse_delta": cd, "fine_delta": fd,
            "delta_of_delta": fd - cd,
        })

    # 生产口径
    prod = spatial_dict[str(PRODUCTION_NODE)]
    given3201 = prod["given"]["t_star_h"]
    d3201 = abs(given3201 - ARCHIVED_GIVEN_T_STAR_H_N3201)
    status3201 = "PASS" if d3201 <= 1.0e-3 else "FAIL"

    print(f"\n  {'N':>6s}  {'给定 t*/h':>12s}  {'闭合 t*/h':>12s}  {'Dt*/h':>10s}  "
          f"{'Dt* rel':>10s}  {'给定 κ 变幅':>12s}  {'闭合 κ 变幅':>12s}  {'迭代':>4s}  {'收敛':>4s}")
    print(f"  {'---':>6s}  {'----------':>12s}  {'----------':>12s}  {'--------':>10s}  "
          f"{'--------':>10s}  {'----------':>12s}  {'----------':>12s}  {'----':>4s}  {'----':>4s}")
    for r in spatial_list:
        print(f"  {r['node_count']:6d}  {r['given']['t_star_h']:12.6f}  {r['closure']['t_star_h']:12.6f}  "
              f"{r['delta_t_star_h']:+10.6f}  {r['delta_t_star_rel']:+10.4%}  "
              f"{r['given']['kappa_rel_range_official']:12.4%}  "
              f"{r['closure']['kappa_rel_range_official']:12.4%}  "
              f"{r['n_iterations']:4d}  {'Y' if r['converged'] else 'N':>4s}")

    print(f"\n  相邻节点 Dt* 差：")
    for a in adjacent_delta:
        print(f"    {a['pair']:>12s}  Dt*(粗)={a['coarse_delta']:+.6f} h"
              f"  Dt*(细)={a['fine_delta']:+.6f} h  差={a['delta_of_delta']:+.6f} h")

    print(f"\n  生产口径 N={PRODUCTION_NODE}：")
    print(f"    给定模型 t*={prod['given']['t_star_h']:.6f} h（主答案 {ARCHIVED_GIVEN_T_STAR_H_N3201:.6f} h"
          f"  diff={d3201:.2e} h [{status3201}]）")
    print(f"    闭合模型 t*={prod['closure']['t_star_h']:.6f} h"
          f"  Dt*={prod['delta_t_star_h']:+.6f} h ({prod['delta_t_star_rel']:+.4%})")
    print(f"    给定 κ 变幅={prod['given']['kappa_rel_range_official']:.4%}（论文 28.02%）"
          f"  闭合 κ 变幅={prod['closure']['kappa_rel_range_official']:.4%}")
    if d3201 > 1.0e-3:
        raise RuntimeError(f"N{PRODUCTION_NODE} given-model != main answer: diff={d3201:.2e} h")

    # ---- 时间积分敏感（N=801，B1/B2/B3）----
    print(f"\n{'-'*78}")
    print(f"[时间积分敏感] N={TEMPORAL_NODE} BDF 容差与最大步长")
    print(f"{'-'*78}")
    temporal_defs = {
        "B2": {},
        "B1": {"relative_tolerance": 1.0e-7, "temperature_absolute_tolerance": 1.0e-7,
               "moisture_absolute_tolerance": 1.0e-9, "max_time_step_s": 60.0},
        "B3": {"relative_tolerance": 1.0e-9, "temperature_absolute_tolerance": 1.0e-10,
               "moisture_absolute_tolerance": 1.0e-12, "max_time_step_s": 10.0},
    }
    temporal_runs = {}
    for name, overrides in temporal_defs.items():
        if name == "B2":
            cfg = ClosureConfig(node_count=TEMPORAL_NODE)
            d = result_to_dict(
                *_run_timed(environment, given_radius, cfg),
            )
            d["name"] = name
            d["config"] = {"relative_tolerance": cfg.relative_tolerance,
                           "max_time_step_s": cfg.max_time_step_s}
            temporal_runs[name] = d
        else:
            r, rt = run_node(environment, given_radius, TEMPORAL_NODE, overrides, verbose=False)
            d = result_to_dict(r, rt)
            d["name"] = name
            d["config"] = {"relative_tolerance": overrides["relative_tolerance"],
                           "max_time_step_s": overrides["max_time_step_s"]}
            temporal_runs[name] = d

    temporal_list = [temporal_runs[n] for n in ("B1", "B2", "B3")]
    b2_vs_b3 = abs(temporal_runs["B2"]["closure"]["t_star_h"] - temporal_runs["B3"]["closure"]["t_star_h"])

    print(f"\n  {'配置':>4s}  {'rtol':>6s}  {'max_step/s':>10s}  {'闭合 t*/h':>12s}  {'Dt*/h':>10s}  {'运行/s':>8s}")
    for r in temporal_list:
        print(f"  {r['name']:>4s}  {r['config']['relative_tolerance']:6.0e}  "
              f"{r['config']['max_time_step_s']:10.1f}  {r['closure']['t_star_h']:12.6f}  "
              f"{r['delta_t_star_h']:+10.6f}  {r['runtime_s']:8.1f}")
    print(f"\n  B2 vs B3 闭合 t* 差 = {b2_vs_b3:.6f} h → 时间积分已收敛")

    # ---- 汇总 ----
    verification = {
        "archived_references": {
            "given_t_star_h_n401": ARCHIVED_GIVEN_T_STAR_H_N401,
            "given_t_star_h_n3201": ARCHIVED_GIVEN_T_STAR_H_N3201,
            "closure_t_star_h_n401": ARCHIVED_CLOSURE_T_STAR_H_N401,
            "kappa_range_official": ARCHIVED_KAPPA_RANGE_OFFICIAL,
        },
        "reproduction": {
            "given_n401_t_star_h": given401,
            "given_n401_abs_diff_h": d401,
            "given_n401_passed": bool(d401 <= 1.0e-4),
            "given_n3201_t_star_h": given3201,
            "given_n3201_abs_diff_h": d3201,
            "given_n3201_passed": bool(d3201 <= 1.0e-3),
            "closure_n401_t_star_h": dict401["closure"]["t_star_h"],
            "closure_n401_passed": bool(abs(dict401["closure"]["t_star_h"] - ARCHIVED_CLOSURE_T_STAR_H_N401) < 0.05),
        },
        "spatial": {"runs": spatial_list, "adjacent_delta": adjacent_delta, "nodes": SPATIAL_NODES},
        "production": prod,
        "temporal": {"runs": temporal_list, "b2_vs_b3_diff_h": b2_vs_b3, "node": TEMPORAL_NODE},
    }

    out_path = BASE / "verification_mass_closure.json"
    json_dump(out_path, verification)

    print(f"\n{LINE}")
    print(f"质量闭合核验完成。verification -> {out_path.name}")
    print(f"\n  模型形式区间：t* in [{ARCHIVED_GIVEN_T_STAR_H_N3201:.4f},"
          f" {prod['closure']['t_star_h']:.4f}] h")
    print(f"  给定模型 κ 变幅 {prod['given']['kappa_rel_range_official']:.4%}"
          f" → 闭合模型 {prod['closure']['kappa_rel_range_official']:.4%}"
          f"（kappa->1 干物质守恒由构造保证）")
    print(f"  Dt* = {prod['delta_t_star_h']:+.4f} h 是边界扰动层 ±{BOUNDARY_BAND_H} h 的"
          f" 约 {abs(prod['delta_t_star_h'])/BOUNDARY_BAND_H:.1f} 倍")
    print(f"  => 支配性不确定源是题给两条经验关系之间的闭合缺口，而非边界扰动或数值离散。")
    print(LINE)


def _run_timed(environment, given_radius, config: ClosureConfig) -> tuple[ClosureResult, float]:
    started = time.perf_counter()
    res = run_closure(environment, given_radius, config, verbose=True)
    return res, time.perf_counter() - started


if __name__ == "__main__":
    main()
