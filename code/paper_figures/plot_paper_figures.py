"""论文正文图1–图5的可复现绘图脚本（agent_A，认领 @agent_C 2026-09-12T06:50:43Z 画图任务）。

数据一律取自已提交的结果文件，不新跑物理模型：
- 图1 results/problem1_improved/result1.xlsx（温度/水分浓度，t=1..1800 s）
- 图2 results/problem2_fvm_bdf/result2.xlsx（温度/水分浓度，t=1..10800 s）
- 图3 results/problem3_fvm_bdf/result3.xlsx + verification.json（t*=57.172706 h / 首个60 s 达标 57.183333 h）
- 图4 results/problem4_fvm_bdf/result4.xlsx + verification.json（shrinkage_ablation：50.8245 h vs 129.0944 h）
      半径轨迹 R(t) 由 code/problem4_fvm_bdf/run_and_verify.load_inputs 读本机 附件/附件2.xlsx（与求解同口径）
- 图5 results/global_sensitivity/pce_validation.json + high_fidelity_checks.json + sobol_indices.json

输出：results/paper_figures/figN_*.png（600 dpi）与同名 .pdf（矢量）。
图内标题、坐标、图例、色条、注释均中文；FVM/BDF/PCE 等通用缩写保留。
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import openpyxl

REPO = Path(__file__).resolve().parents[2]
OUT = REPO / "results" / "paper_figures"
OUT.mkdir(parents=True, exist_ok=True)

plt.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei", "SimSun"]
plt.rcParams["axes.unicode_minus"] = False
plt.rcParams["figure.dpi"] = 110

PARAM_CN = {
    "activation_temperature_factor": "活化温度因子",
    "diffusivity_prefactor_factor": "扩散前因子",
    "ambient_temperature_delta_c": "环境温度偏差",
    "shrinkage_amplitude_factor": "收缩幅度因子",
    "mass_transfer_coefficient_factor": "传质系数因子",
    "mass_transfer_factor": "传质系数因子",
}


def load_field(xlsx: Path, sheet: str):
    """读 (时间/s 一维, 半径/cm 一维, 场矩阵[nt, nr])；'药材表面' 列单独返回。"""
    wb = openpyxl.load_workbook(xlsx, read_only=True, data_only=True)
    ws = wb[sheet]
    rows = list(ws.iter_rows(values_only=True))
    wb.close()
    header = rows[0]
    radius, surface_idx = [], None
    for j, name in enumerate(header[1:], start=1):
        if isinstance(name, str) and not name.replace(".", "", 1).isdigit():
            surface_idx = j
        else:
            radius.append(float(name))
    t = np.array([float(r[0]) for r in rows[1:]])
    cols = [j for j in range(1, len(header)) if j != surface_idx]
    field = np.array([[np.nan if r[j] is None else float(r[j]) for j in cols] for r in rows[1:]])
    surface = (
        np.array([np.nan if r[surface_idx] is None else float(r[surface_idx]) for r in rows[1:]])
        if surface_idx
        else None
    )
    return t, np.array(radius), field, surface


def save(fig, slug: str) -> None:
    fig.tight_layout()
    fig.savefig(OUT / f"{slug}.png", dpi=600)
    fig.savefig(OUT / f"{slug}.pdf")
    plt.close(fig)
    print("written:", slug)


def fig1() -> None:
    p = REPO / "results" / "problem1_improved" / "result1.xlsx"
    tt, rr, T, _ = load_field(p, "温度")
    _, _, C, _ = load_field(p, "水分浓度")
    fig, axes = plt.subplots(1, 2, figsize=(9.6, 3.9), sharex=True)
    for ax, mat, ylabel in ((axes[0], T, "温度/℃"), (axes[1], C, "水分浓度/(kg/kg)")):
        for ts in (100, 600, 1200, 1800):
            i = int(np.argmin(np.abs(tt - ts)))
            ax.plot(rr, mat[i], marker="o", ms=2.6, lw=1.3, label=f"{int(tt[i])} s")
        ax.set_xlabel("距中心半径/cm")
        ax.set_ylabel(ylabel)
        ax.grid(alpha=0.3)
        ax.legend(title="预热时间", fontsize=8, title_fontsize=8)
    axes[0].set_title("(a) 温度径向分布")
    axes[1].set_title("(b) 水分浓度径向分布")
    fig.suptitle("图1 问题一预热阶段药材温度与水分浓度的径向演化", fontsize=11)
    save(fig, "fig1_problem1_radial")


def fig2() -> None:
    p = REPO / "results" / "problem2_fvm_bdf" / "result2.xlsx"
    tt, rr, T, _ = load_field(p, "温度")
    _, _, C, _ = load_field(p, "水分浓度")
    th = tt / 3600.0
    fig, axes = plt.subplots(1, 2, figsize=(10.2, 4.1))
    for ax, mat, cblabel, title in (
        (axes[0], T, "温度/℃", "(a) 温度 T(r,t)"),
        (axes[1], C, "水分浓度/(kg/kg)", "(b) 水分浓度 C(r,t)"),
    ):
        m = ax.pcolormesh(th, rr, mat.T, shading="nearest", cmap="viridis")
        ax.contour(th, rr, mat.T, levels=6, colors="k", linewidths=0.5, alpha=0.55)
        cb = fig.colorbar(m, ax=ax)
        cb.set_label(cblabel)
        ax.set_xlabel("时间/h")
        ax.set_ylabel("距中心半径/cm")
        ax.set_title(title)
    fig.suptitle("图2 变物性热湿耦合条件下温度与水分浓度的时空演化", fontsize=11)
    save(fig, "fig2_problem2_heatmap")


def fig3() -> None:
    p = REPO / "results" / "problem3_fvm_bdf" / "result3.xlsx"
    tt, rr, C, _ = load_field(p, "水分浓度")
    ver = json.loads((REPO / "results" / "problem3_fvm_bdf" / "verification.json").read_text(encoding="utf-8"))
    t_star = ver["final"]["continuous_event_time_h"]
    t_first = ver["final"]["first_strictly_compliant_60s_time_h"]
    th = tt / 3600.0
    fig, axes = plt.subplots(1, 2, figsize=(10.4, 4.1))
    ax = axes[0]
    m = ax.pcolormesh(th, rr, C.T, shading="nearest", cmap="viridis")
    cs = ax.contour(th, rr, C.T, levels=[0.15], colors="w", linewidths=1.4)
    ax.clabel(cs, fmt="C=0.15", fontsize=8)
    fig.colorbar(m, ax=ax).set_label("水分浓度/(kg/kg)")
    ax.set_xlabel("时间/h")
    ax.set_ylabel("距中心半径/cm")
    ax.set_title("(a) 水分浓度时空演化与达标等值线")
    ax = axes[1]
    ax.plot(th, C[:, 0], lw=1.5, label="中心水分")
    ax.plot(th, C[:, -1], lw=1.5, label="表面水分")
    ax.plot(th, C.max(axis=1), lw=1.2, ls="--", label="全域最大水分")
    ax.axhline(0.15, color="k", lw=1.0, ls=":", label="达标阈值 C=0.15")
    ax.axvline(t_star, color="C3", lw=1.2, label=f"连续临界时间 {t_star:.4f} h")
    ax.plot([t_first], [0.15], marker="v", color="C3", ms=7, label=f"首个60 s达标 {t_first:.4f} h")
    ax.set_xlabel("时间/h")
    ax.set_ylabel("水分浓度/(kg/kg)")
    ax.set_title("(b) 关键位置水分演化与全域达标时刻")
    ax.grid(alpha=0.3)
    ax.legend(fontsize=7.5, loc="upper right")
    fig.suptitle("图3 固定半径条件下水分浓度演化及全域达标时刻", fontsize=11)
    save(fig, "fig3_problem3_event")


def fig4() -> None:
    sys.path.insert(0, str(REPO / "code" / "problem4_fvm_bdf"))
    from run_and_verify import load_inputs  # 只读复用稳定 API

    env, radius = load_inputs(REPO / "附件" / "附件1.xlsx", REPO / "附件" / "附件2.xlsx")
    p = REPO / "results" / "problem4_fvm_bdf" / "result4.xlsx"
    tt, rr, C, surface = load_field(p, "水分浓度")
    ver = json.loads((REPO / "results" / "problem4_fvm_bdf" / "verification.json").read_text(encoding="utf-8"))
    sa = ver["shrinkage_ablation"]
    th = tt / 3600.0
    Rt = np.array([radius.radius_cm_at(t) for t in tt])
    mask = np.isnan(C) | np.array([[r > Rt[i] for r in rr] for i in range(len(tt))])
    Cm = np.ma.masked_array(C, mask=mask)
    fig, axes = plt.subplots(1, 2, figsize=(10.6, 4.2))
    ax = axes[0]
    ax.set_facecolor("#e8e8e8")
    m = ax.pcolormesh(th, rr, Cm.T, shading="nearest", cmap="viridis")
    ax.plot(th, Rt, color="w", lw=1.6, label="移动边界 R(t)")
    ax.plot(th, Rt, color="k", lw=0.7, ls="--")
    fig.colorbar(m, ax=ax).set_label("水分浓度/(kg/kg)")
    ax.set_xlabel("时间/h")
    ax.set_ylabel("距中心半径/cm")
    ax.set_title("(a) 物理坐标水分演化与移动边界（灰色=已收缩区域）")
    ax.legend(fontsize=8, loc="upper right")
    ax = axes[1]
    names = ["动态半径\n（主答案）", "固定半径 2.0 cm\n（反事实对照）"]
    vals = [sa["dynamic_radius_event_time_h"], sa["fixed_radius_event_time_h"]]
    bars = ax.bar(names, vals, color=["C0", "C4"], width=0.5)
    for b, v in zip(bars, vals):
        ax.text(b.get_x() + b.get_width() / 2, v + 2, f"{v:.4f} h", ha="center", fontsize=9)
    ax.set_ylabel("连续临界时间/h")
    ax.set_title(f"(b) 收缩作用消融对照（缩短 {sa['time_reduction_h']:.4f} h）")
    ax.grid(alpha=0.3, axis="y")
    ax.text(
        0.02, 0.97,
        "口径区分：50.8245 h 为主答案；129.0944 h 为反事实对照；\n"
        "Euler 空间坐标模型 52.3842 h 仅作模型形式敏感性对照；\n"
        "质量闭合情景 60.7443 h 为替代闭合条件，均非并列答案。",
        transform=ax.transAxes, va="top", fontsize=7.2,
        bbox=dict(boxstyle="round", fc="#fff8dc", ec="gray", lw=0.6),
    )
    fig.suptitle("图4 半径收缩条件下水分浓度演化及收缩作用对照", fontsize=11)
    save(fig, "fig4_problem4_moving_boundary")


def fig5() -> None:
    gs = REPO / "results" / "global_sensitivity"
    pv = json.loads((gs / "pce_validation.json").read_text(encoding="utf-8"))
    hf = json.loads((gs / "high_fidelity_checks.json").read_text(encoding="utf-8"))
    sb = json.loads((gs / "sobol_indices.json").read_text(encoding="utf-8"))
    val = pv["validation"]
    y_val, y_pred = np.array(val["event_time_h"]), np.array(val["prediction_h"])
    hf_rows = hf["rows"]
    y_hf = np.array([r["pde_event_time_h"] for r in hf_rows])
    p_hf = np.array([r["pce_prediction_h"] for r in hf_rows])
    fig, axes = plt.subplots(1, 2, figsize=(10.4, 4.2))
    ax = axes[0]
    lo = min(y_val.min(), y_pred.min(), y_hf.min(), p_hf.min()) * 0.98
    hi = max(y_val.max(), y_pred.max(), y_hf.max(), p_hf.max()) * 1.02
    ax.plot([lo, hi], [lo, hi], "k--", lw=0.9, label="1:1 参考线")
    ax.scatter(y_val, y_pred, s=18, facecolors="none", edgecolors="C0", label=f"N801 独立验证点（{len(y_val)}）")
    ax.scatter(y_hf, p_hf, s=34, marker="^", color="C3", label=f"N3201 复核点（{len(y_hf)}）")
    ax.set_xlabel("高保真 PDE 临界时间/h")
    ax.set_ylabel("PCE 代理预测/h")
    ax.set_title(f"(a) PCE 验证（Q²={pv['metrics']['q_squared_independent']:.9f}，RMSE={pv['metrics']['rmse_h']:.4f} h）")
    ax.grid(alpha=0.3)
    ax.legend(fontsize=8)
    ax = axes[1]
    rows = sb["analytical"]["rows"]
    labels = [PARAM_CN.get(r["parameter"], r["parameter"]) for r in rows]
    ypos = np.arange(len(rows))
    s1 = np.array([r["first_order"] for r in rows])
    st = np.array([r["total_order"] for r in rows])
    e1 = np.array([[r["first_order"] - r["first_order_95_interval"][0], r["first_order_95_interval"][1] - r["first_order"]] for r in rows]).T
    et = np.array([[r["total_order"] - r["total_order_95_interval"][0], r["total_order_95_interval"][1] - r["total_order"]] for r in rows]).T
    ax.errorbar(s1, ypos - 0.16, xerr=e1, fmt="o", ms=4.5, color="C0", capsize=2.5, label="一阶指数")
    ax.errorbar(st, ypos + 0.16, xerr=et, fmt="s", ms=4.5, color="C4", capsize=2.5, label="总效应指数")
    ax.set_yticks(ypos)
    ax.set_yticklabels(labels)
    ax.set_xlabel("Sobol 敏感性指数")
    ax.set_title("(b) 干燥时间的 Sobol 全局敏感性")
    ax.grid(alpha=0.3, axis="x")
    ax.legend(fontsize=8, loc="center right")
    fig.suptitle("图5 PCE 代理模型预测精度及干燥时间的 Sobol 全局敏感性", fontsize=11)
    save(fig, "fig5_pce_sobol")


if __name__ == "__main__":
    fig1()
    fig2()
    fig3()
    fig4()
    fig5()
    print("all figures done ->", OUT)
