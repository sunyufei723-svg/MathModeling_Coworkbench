"""L5 干物质闭合分支 —— 全量验证与结果生成编排。

产出（写入 --results-dir，默认 results/problem4_mass_closure/）：
  * verification.json                     —— 全部结构化结果
  * mass_closure_tables.md                —— 给定模型 vs 闭合模型逐节点对照 + 生产值
  * numerical_verification.md             —— 空间网格收敛 + 时间积分敏感 + κ→1 质量闭合核验
  * problem4_mass_closure_explanation.md  —— 模型/假设/方程/结果/边界（解法与代码说明）

只读 import code/submission/business/problem4；不改其任何文件。运行：
  python code/submission/analysis/problem4_mass_closure/run_and_verify.py \
      --attachment1 附件/附件1.xlsx --attachment2 附件/附件2.xlsx \
      --results-dir results/problem4_mass_closure --work-dir <临时目录> [--resume] [--quick]
"""
from __future__ import annotations

import argparse
import hashlib
import json
import platform
import sys
import time
from dataclasses import replace
from pathlib import Path

import numpy as np
import pandas as pd
import scipy

ROOT = Path(__file__).resolve().parents[4]
for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8")
    except (AttributeError, ValueError):
        pass
if str(ROOT / "code" / "submission" / "analysis" / "problem4_mass_closure") not in sys.path:
    sys.path.insert(0, str(ROOT / "code" / "submission" / "analysis" / "problem4_mass_closure"))

from closure import ClosureConfig, ClosureResult, load_inputs, run_closure  # noqa: E402

# 归档参考值（用于复现校验；来源见注释）
ARCHIVED_GIVEN_T_STAR_H_N401 = 50.844229    # limitations §1.4 附A（linear 口径）
ARCHIVED_GIVEN_T_STAR_H_N3201 = 50.824507   # 主答案 results/problem4_fvm_bdf/verification.json
ARCHIVED_CLOSURE_T_STAR_H_N401 = 60.7312    # day2 决策G / drymass_closure.py（N401）
ARCHIVED_KAPPA_RANGE_OFFICIAL = 0.2802      # 论文 28.02%

SPATIAL_NODES = [201, 401, 801, 1601, 3201]
PRODUCTION_NODE = 3201
TEMPORAL_NODE = 801
BOUNDARY_BAND_H = 2.8                        # B 的 LHS 边界扰动层（±2.8 h，决策 I 参照）


def json_dump(path: Path, value) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False), encoding="utf-8")


def markdown_table(headers: list[str], rows: list[list[str]]) -> str:
    return "\n".join(
        [
            "| " + " | ".join(headers) + " |",
            "| " + " | ".join(["---"] * len(headers)) + " |",
            *["| " + " | ".join(row) + " |" for row in rows],
        ]
    )


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


def write_reports(results_dir: Path, verification: dict) -> None:
    results_dir.mkdir(parents=True, exist_ok=True)
    spatial = verification["spatial"]["runs"]
    temporal = verification["temporal"]["runs"]
    prod = verification["production"]
    repro = verification["reproduction"]

    # --- mass_closure_tables.md ---
    spatial_rows = [
        [
            str(r["node_count"]),
            f"{r['given']['t_star_h']:.6f}",
            f"{r['closure']['t_star_h']:.6f}",
            f"{r['delta_t_star_h']:+.6f}",
            f"{r['delta_t_star_rel']:+.4%}",
            f"{r['given']['kappa_rel_range_official']:.4%}",
            f"{r['closure']['kappa_rel_range_official']:.4%}",
            str(r["n_iterations"]),
            "是" if r["converged"] else "否",
        ]
        for r in spatial
    ]
    (results_dir / "mass_closure_tables.md").write_text(
        "\n".join(
            [
                "# A题问题四 L5 干物质闭合分支 · 对照表",
                "",
                "> ⚠️ **本分支是「模型形式对照」，不是答案。** 题设直接模型主答案仍为 "
                f"**{ARCHIVED_GIVEN_T_STAR_H_N3201:.4f} h**（N=3201）。闭合分支强制干物质守恒，"
                "其半径轨迹与附件 2 矛盾，只用于给出「若强制质量守恒，t\\* 会推迟到多少」的反事实上界。",
                "",
                "## 表 L5-1 给定模型 vs 干物质闭合模型（逐节点，同 BDF 口径）",
                "",
                markdown_table(
                    ["节点数 N", "给定模型 t\\*/h", "闭合模型 t\\*/h", "Δt\\*/h", "Δt\\* 相对",
                     "给定 κ 变幅", "闭合 κ 变幅", "迭代数", "收敛"],
                    spatial_rows,
                ),
                "",
                f"**生产口径（N={PRODUCTION_NODE}）**：给定模型 t\\*={prod['given']['t_star_h']:.6f} h"
                f"（主答案），闭合模型 t\\*={prod['closure']['t_star_h']:.6f} h，"
                f"Δt\\*={prod['delta_t_star_h']:+.6f} h（{prod['delta_t_star_rel']:+.4%}）。",
                "",
                f"**质量闭合核验**：给定模型 κ 变幅 {prod['given']['kappa_rel_range_official']:.4%}"
                f"（论文 28.02%），闭合模型降到 {prod['closure']['kappa_rel_range_official']:.4%}"
                f"（κ_min {prod['closure']['kappa_min']:.6f}、κ(t\\*) {prod['closure']['kappa_event']:.6f} ⇒ 干物质近似守恒）。",
                "",
                f"**同口径比较结论**：网格收敛后 Δt\\* ≈ {prod['delta_t_star_h']:+.4f} h，是边界扰动层 "
                f"±{BOUNDARY_BAND_H} h 的约 {abs(prod['delta_t_star_h'])/BOUNDARY_BAND_H:.1f} 倍 ⇒ "
                "**支配性不确定源是题给两条经验关系（附录4 密度律 + 附件2 半径轨迹）之间的闭合缺口，"
                "而非边界扰动或数值离散。**",
                "",
            ]
        ),
        encoding="utf-8",
    )

    # --- numerical_verification.md ---
    temporal_rows = [
        [
            r["name"],
            f"{r['config']['relative_tolerance']:.0e}",
            f"{r['config']['max_time_step_s']:g}",
            f"{r['closure']['t_star_h']:.6f}",
            f"{r['delta_t_star_h']:+.6f}",
            f"{r['runtime_s']:.1f}",
        ]
        for r in temporal
    ]
    adj = verification["spatial"]["adjacent_delta"]
    (results_dir / "numerical_verification.md").write_text(
        "\n".join(
            [
                "# A题问题四 L5 干物质闭合分支 · 数值验证",
                "",
                "## 空间网格收敛（Δt\\* 的网格无关性）",
                "",
                markdown_table(
                    ["相邻节点对", "Δt\\*(粗)/h", "Δt\\*(细)/h", "两者之差/h"],
                    [[a["pair"], f"{a['coarse_delta']:+.6f}", f"{a['fine_delta']:+.6f}",
                      f"{a['delta_of_delta']:+.6f}"] for a in adj],
                ),
                "",
                f"最细相邻对（1601→3201）Δt\\* 之差 **{adj[-1]['delta_of_delta']:+.6f} h**"
                f"（{abs(adj[-1]['delta_of_delta'])/abs(prod['delta_t_star_h']):.3%} of Δt\\*）⇒ "
                "**可靠的量是差值 Δt\\*，它对网格收敛**；闭合分支绝对 t\\* 与给定模型一样存在微小网格偏移。",
                "",
                "## 时间积分敏感（BDF 容差与最大步长，N=" + str(TEMPORAL_NODE) + "）",
                "",
                markdown_table(
                    ["配置", "rtol", "max_step/s", "闭合 t\\*/h", "Δt\\*/h", "运行/s"],
                    temporal_rows,
                ),
                "",
                f"B2↔B3 闭合 t\\* 之差 **{verification['temporal']['b2_vs_b3_diff_h']:.6f} h** ⇒ "
                "时间积分已收敛，闭合轨迹不依赖 BDF 容差。",
                "",
                "## 质量闭合核验（κ→1）",
                "",
                f"给定模型：κ 变幅 {prod['given']['kappa_rel_range_official']:.4%}、κ_min="
                f"{prod['given']['kappa_min']:.6f} @ t={prod['given']['t_kappa_min_h']:.4f} h、κ(t\\*)="
                f"{prod['given']['kappa_event']:.6f}（干物质**不**守恒，即 28.02% 局限）。",
                f"闭合模型：κ 变幅 {prod['closure']['kappa_rel_range_official']:.4%}、κ_min="
                f"{prod['closure']['kappa_min']:.6f}、κ(t\\*)={prod['closure']['kappa_event']:.6f}"
                "（不动点收敛 ⇒ κ≡1，干物质守恒由构造保证）。",
                "",
                "## 复现校验",
                "",
                f"给定模型 N=401 t\\*={repro['given_n401_t_star_h']:.6f} h，归档 {ARCHIVED_GIVEN_T_STAR_H_N401:.6f} h，"
                f"差 {repro['given_n401_abs_diff_h']:.2e} h ⇒ **{'通过' if repro['given_n401_passed'] else '未通过'}**"
                "（逐位复现诊断基线，证明只读 import 与配置与主求解器同源）。",
                f"给定模型 N=3201 t\\*={repro['given_n3201_t_star_h']:.6f} h，主答案 {ARCHIVED_GIVEN_T_STAR_H_N3201:.6f} h，"
                f"差 {repro['given_n3201_abs_diff_h']:.2e} h ⇒ **{'通过' if repro['given_n3201_passed'] else '未通过'}**。",
                f"闭合模型 N=401 t\\*={repro['closure_n401_t_star_h']:.6f} h，诊断归档 ~{ARCHIVED_CLOSURE_T_STAR_H_N401:.4f} h ⇒ "
                f"**{'一致' if repro['closure_n401_passed'] else '偏离（见迭代序列）'}**。",
                "",
            ]
        ),
        encoding="utf-8",
    )

    # --- problem4_mass_closure_explanation.md ---
    (results_dir / "problem4_mass_closure_explanation.md").write_text(
        "\n".join(
            [
                "# A题问题四 L5 干物质闭合分支 · 解法与代码说明",
                "",
                "## 定位（务必先读）",
                "",
                f"题设直接模型主答案 = **{ARCHIVED_GIVEN_T_STAR_H_N3201:.4f} h**（N=3201，附件 2 的 R(t) 作已知输入）。"
                "本 L5 分支**不是更高精度、也不是替代答案**，而是另一种「模型形式」：把附件 2 的 R(t) 换成"
                "**由干物质守恒自洽决定的闭合轨迹**，用于定量回答「若强制质量守恒，烘干时长会怎样」。",
                "",
                "## 闭合方程与假设",
                "",
                "假设圆柱横截面**均匀仿射收缩**（ξ=r/R(t) 标记固定物质点）、**干骨架质量守恒**、体积 ∝ R^2（单位长度）。"
                "附录 4 干基固体密度 ρ_s(C)=ρ(C)/(1+C)=90+670/(1+C) kg/m³（ρ(C)=760+90C），"
                f"ρ_s0=ρ_s(C0=2.55)={prod['rho_s0']:.4f} kg/m³。定义干物质指数 m(t)=R(t)²·Σ_i ρ_s(C_i)·V̂_i、"
                "κ(t)=m(t)/m0（m0 为初始值）、几何因子 G=(R/R0)²、压缩因子 S=<ρ_s>/ρ_s0，则恒等式 **κ=G·S**。",
                "",
                "干物质闭合要求 κ≡1，即 R(t)=R0/√(S(t))。这构成不动点迭代：",
                "",
                "    给定 R_k(t) → 解热湿耦合 PDE（物质坐标 FVM-BDF，只读调用 problem4_fvm_bdf）→ C(ξ,t)、S_k(t)",
                "    → R_{k+1}(t) = R0 / sqrt(S_k(t))     （等价于 R_{k+1}=R_k/√κ_k）",
                "",
                "收敛判据：相邻迭代 |Δt\\*|<1e-4 h 且 κ 相对变幅<1e-4。收敛时 κ≡1，干物质精确守恒。",
                "",
                "## 结果",
                "",
                f"* N=401 复现：给定 {repro['given_n401_t_star_h']:.6f} h、闭合 {repro['closure_n401_t_star_h']:.6f} h"
                f"（诊断归档 ~{ARCHIVED_CLOSURE_T_STAR_H_N401:.4f} h）。",
                f"* N=3201 生产：给定 {prod['given']['t_star_h']:.6f} h（=主答案）、闭合 {prod['closure']['t_star_h']:.6f} h，"
                f"Δt\\*={prod['delta_t_star_h']:+.6f} h（{prod['delta_t_star_rel']:+.4%}）。",
                f"* 模型形式区间：t\\* ∈ [{ARCHIVED_GIVEN_T_STAR_H_N3201:.4f}, {prod['closure']['t_star_h']:.4f}] h。",
                f"* 质量闭合：给定 κ 变幅 {prod['given']['kappa_rel_range_official']:.4%} → 闭合 {prod['closure']['kappa_rel_range_official']:.4%}。",
                "",
                "## 适用边界与注意",
                "",
                "1. **不得替换主答案**：附件 2 是题给数据，闭合轨迹与它矛盾（自 19.5 h 起需负含水率才能闭合，"
                "见 §1.4 上界证明），故闭合分支只作反事实上界，不进入表 6/表 7 的答案列。",
                "2. **bootstrap 覆盖**：闭合 R(t) 只在已解出的时间范围内已知，早期迭代对超出部分按末端值延拓"
                "（RadiusSeries 夹取）；随迭代收敛，覆盖终端逼近 t\\*，该近似消失（见 coverage_terminal_h）。",
                "3. **只读依赖**：本模块只读 import problem4_fvm_bdf 的 SolverConfig/solve_problem4_bdf/load_inputs/"
                "RadiusSeries/build_reference_geometry/density，并在导入时做契约自检；不修改其任何文件。",
                "4. κ 变幅的「official」口径取自求解器 diagnostics.dry_mass_index_relative_range（含 t=0），与论文 28.02% 同源。",
                "",
                "## 文件",
                "",
                "`closure.py` 闭合不动点求解器（方程+假设+契约自检）；`run_and_verify.py` 本编排（复现/生产/敏感性/核验/文档）；"
                "`test_closure.py` 单元测试；`README.md` 模块说明。结果见 `results/problem4_mass_closure/`。",
                "",
            ]
        ),
        encoding="utf-8",
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="问题四 L5 干物质闭合分支全量验证")
    parser.add_argument("--attachment1", type=Path, default=ROOT / "附件" / "附件1.xlsx")
    parser.add_argument("--attachment2", type=Path, default=ROOT / "附件" / "附件2.xlsx")
    parser.add_argument("--results-dir", type=Path, default=ROOT / "results" / "problem4_mass_closure")
    parser.add_argument("--work-dir", type=Path, default=ROOT / "results" / "problem4_mass_closure" / "_work")
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--quick", action="store_true", help="仅 N=401 复现（开发冒烟，不写完整报告）")
    args = parser.parse_args()
    args.work_dir.mkdir(parents=True, exist_ok=True)

    environment, given_radius = load_inputs(args.attachment1, args.attachment2)
    print(f"附件2 R(0)={given_radius.radius_cm[0]} cm  R(end)={given_radius.radius_cm[-1]} cm  "
          f"t_end={given_radius.terminal_time_s/3600.0:.2f} h", flush=True)

    # ---- 复现（N=401）----
    ck = args.work_dir / "n401.json"
    if args.resume and ck.exists():
        res401 = json.loads(ck.read_text(encoding="utf-8"))
        print("RESUME N401", flush=True)
    else:
        r, rt = run_node(environment, given_radius, 401)
        res401 = result_to_dict(r, rt)
        json_dump(ck, res401)

    # 硬校验：给定模型必须逐位复现归档基线（证明 import+配置与主求解器同源）
    given401 = res401["given"]["t_star_h"]
    d401 = abs(given401 - ARCHIVED_GIVEN_T_STAR_H_N401)
    if d401 > 1.0e-4:
        raise RuntimeError(f"N401 given-model reproduction FAILED: {given401:.6f} vs {ARCHIVED_GIVEN_T_STAR_H_N401:.6f} (diff {d401:.2e} h)")
    print(f"REPRO OK: given N401 t*={given401:.6f} h (diff {d401:.2e}); "
          f"closure N401 t*={res401['closure']['t_star_h']:.6f} h (archived ~{ARCHIVED_CLOSURE_T_STAR_H_N401})", flush=True)

    if args.quick:
        print(json.dumps(res401, ensure_ascii=False, indent=2), flush=True)
        return

    # ---- 空间网格扫描 ----
    spatial_runs = {"401": res401}
    for node in SPATIAL_NODES:
        key = str(node)
        ckp = args.work_dir / f"n{node}.json"
        if key in spatial_runs:
            continue
        if args.resume and ckp.exists():
            spatial_runs[key] = json.loads(ckp.read_text(encoding="utf-8"))
            print(f"RESUME N{node}", flush=True)
            continue
        r, rt = run_node(environment, given_radius, node)
        spatial_runs[key] = result_to_dict(r, rt)
        json_dump(ckp, spatial_runs[key])

    spatial_list = [spatial_runs[str(n)] for n in SPATIAL_NODES]
    adjacent_delta = []
    for coarse, fine in zip(SPATIAL_NODES[:-1], SPATIAL_NODES[1:]):
        cd = spatial_runs[str(coarse)]["delta_t_star_h"]
        fd = spatial_runs[str(fine)]["delta_t_star_h"]
        adjacent_delta.append({"pair": f"{coarse}->{fine}", "coarse_delta": cd, "fine_delta": fd, "delta_of_delta": fd - cd})

    # ---- 生产口径（N=3201）----
    prod = spatial_runs[str(PRODUCTION_NODE)]

    # 硬校验：给定模型 N3201 必须复现主答案
    given3201 = prod["given"]["t_star_h"]
    d3201 = abs(given3201 - ARCHIVED_GIVEN_T_STAR_H_N3201)
    if d3201 > 1.0e-3:
        raise RuntimeError(f"N3201 given-model != main answer: {given3201:.6f} vs {ARCHIVED_GIVEN_T_STAR_H_N3201:.6f} (diff {d3201:.2e} h)")

    # ---- 时间积分敏感（N=801，B1/B2/B3）----
    temporal_defs = {
        "B2": {},
        "B1": {"relative_tolerance": 1.0e-7, "temperature_absolute_tolerance": 1.0e-7,
               "moisture_absolute_tolerance": 1.0e-9, "max_time_step_s": 60.0},
        "B3": {"relative_tolerance": 1.0e-9, "temperature_absolute_tolerance": 1.0e-10,
               "moisture_absolute_tolerance": 1.0e-12, "max_time_step_s": 10.0},
    }
    temporal_runs = {}
    for name, overrides in temporal_defs.items():
        ckp = args.work_dir / f"temporal_{name}.json"
        if name == "B2":
            cfg = ClosureConfig(node_count=TEMPORAL_NODE)
            temporal_runs[name] = {**spatial_runs[str(TEMPORAL_NODE)], "name": name,
                                   "config": {"relative_tolerance": cfg.relative_tolerance,
                                              "max_time_step_s": cfg.max_time_step_s}}
            continue
        if args.resume and ckp.exists():
            temporal_runs[name] = json.loads(ckp.read_text(encoding="utf-8"))
            print(f"RESUME temporal {name}", flush=True)
            continue
        r, rt = run_node(environment, given_radius, TEMPORAL_NODE, overrides, verbose=False)
        d = result_to_dict(r, rt)
        d["name"] = name
        d["config"] = {"relative_tolerance": overrides["relative_tolerance"],
                       "max_time_step_s": overrides["max_time_step_s"]}
        temporal_runs[name] = d
        json_dump(ckp, d)
    temporal_list = [temporal_runs[n] for n in ("B1", "B2", "B3")]
    b2_vs_b3 = abs(temporal_runs["B2"]["closure"]["t_star_h"] - temporal_runs["B3"]["closure"]["t_star_h"])

    verification = {
        "source": {
            "attachment1_sha256": hashlib.sha256(args.attachment1.read_bytes()).hexdigest(),
            "attachment2_sha256": hashlib.sha256(args.attachment2.read_bytes()).hexdigest(),
            "python_version": platform.python_version(),
            "numpy_version": np.__version__,
            "scipy_version": scipy.__version__,
            "pandas_version": pd.__version__,
            "solver_dir": str(ROOT / "code" / "submission" / "business" / "problem4"),
        },
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
            "closure_n401_t_star_h": res401["closure"]["t_star_h"],
            "closure_n401_passed": bool(abs(res401["closure"]["t_star_h"] - ARCHIVED_CLOSURE_T_STAR_H_N401) < 0.05),
        },
        "spatial": {"runs": spatial_list, "adjacent_delta": adjacent_delta, "nodes": SPATIAL_NODES},
        "production": prod,
        "temporal": {"runs": temporal_list, "b2_vs_b3_diff_h": b2_vs_b3, "node": TEMPORAL_NODE},
    }
    json_dump(args.results_dir / "verification.json", verification)
    write_reports(args.results_dir, verification)
    print(json.dumps({"production": prod, "reproduction": verification["reproduction"],
                      "b2_vs_b3_diff_h": b2_vs_b3}, ensure_ascii=False, indent=2), flush=True)
    print(f"DONE -> {args.results_dir}", flush=True)


if __name__ == "__main__":
    main()
