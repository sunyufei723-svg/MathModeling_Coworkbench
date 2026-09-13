# -*- coding: utf-8 -*-
# 仅生成：q3_q4_numerical_convergence.png
# 依赖：pip install numpy matplotlib

from pathlib import Path

import matplotlib as mpl
import matplotlib.pyplot as plt
import numpy as np
from matplotlib import font_manager


# =========================
# 1. 输出位置与字体
# =========================
OUTPUT = Path(__file__).resolve().with_name(
    "q3_q4_numerical_convergence.png"
)

preferred_fonts = ["SimSun", "Microsoft YaHei", "Noto Serif CJK SC"]
installed_fonts = {font.name for font in font_manager.fontManager.ttflist}
chinese_font = next(
    (name for name in preferred_fonts if name in installed_fonts),
    "DejaVu Sans",
)

mpl.rcParams.update({
    "font.family": chinese_font,
    "axes.unicode_minus": False,
    "pdf.fonttype": 42,
    "ps.fonttype": 42,
    "font.size": 9,
    "axes.labelsize": 9,
    "axes.titlesize": 10,
    "xtick.labelsize": 8,
    "ytick.labelsize": 8,
    "legend.fontsize": 8,
    "axes.linewidth": 0.65,
    "lines.linewidth": 1.45,
    "lines.markersize": 4.5,
})


# =========================
# 2. 已验证的数值数据
# =========================

# 问题三：空间网格加密
dr_q3_cm = np.array([
    0.1,
    0.05,
    0.025,
    0.0125,
    0.00625,
    0.003125,
    0.0015625,
    0.00078125,
])
tstar_q3_h = np.array([
    557.4174000560475,
    226.54526778507412,
    88.13188477770902,
    60.215698454201416,
    57.564806852812566,
    57.237485485619814,
    57.18363298461462,
    57.172706169541755,
])

# 问题四：空间网格加密
nodes_q4 = np.array([201, 401, 801, 1601, 3201])
tstar_q4_h = np.array([
    50.909115678513,
    50.844229259789586,
    50.829109673697936,
    50.825422315121216,
    50.82450698946728,
])

# 问题三：BE--BDF 交叉验证
bdf_q3_h = 57.172706123603106
be_dt_q3_s = np.array([20.0, 10.0, 5.0, 2.5])
be_tstar_q3_h = np.array([
    57.190190972222226,
    57.181423611111114,
    57.177083333333336,
    57.17491319444444,
])

# 问题四：BE--BDF 交叉验证
bdf_q4_h = 50.82450698946728
be_dt_q4_s = np.array([20.0, 10.0, 5.0, 2.5])
be_tstar_q4_h = np.array([
    50.837673611111114,
    50.83116319444444,
    50.82786458333333,
    50.82621527777778,
])

error_q3_s = (be_tstar_q3_h - bdf_q3_h) * 3600.0
error_q4_s = (be_tstar_q4_h - bdf_q4_h) * 3600.0

order_q3 = np.argsort(be_dt_q3_s)
order_q4 = np.argsort(be_dt_q4_s)


# =========================
# 3. 绘图
# =========================
fig, axes = plt.subplots(1, 3, figsize=(7.1, 2.8))

# （a）问题三空间网格收敛
ax = axes[0]
ax.semilogx(dr_q3_cm, tstar_q3_h, "o-", color="#2f6f9f")
ax.invert_xaxis()
ax.set_xticks([0.1, 0.01, 0.001], ["0.1", "0.01", "0.001"])
ax.set_xlabel("内部网格 Δr / cm")
ax.set_ylabel("连续临界时间 t* / h")
ax.set_title("问题三空间加密", pad=5)
ax.set_ylim(30, 590)
ax.grid(True, which="both", color="#d9dde0", lw=0.5)
ax.annotate(
    "57.1727 h",
    xy=(dr_q3_cm[-1], tstar_q3_h[-1]),
    xytext=(0.0022, 95),
    fontsize=7.5,
    arrowprops={
        "arrowstyle": "-",
        "color": "#4d5966",
        "lw": 0.7,
    },
)

# （b）问题四空间网格收敛
ax = axes[1]
ax.semilogx(nodes_q4, tstar_q4_h, "s-", color="#3f8567")
ax.set_xlabel("内部节点数 N")
ax.set_ylabel("连续临界时间 t* / h")
ax.set_title("问题四空间加密", pad=5)
ax.set_ylim(50.82, 50.92)
ax.grid(True, which="both", color="#d9dde0", lw=0.5)
ax.annotate(
    "50.8245 h",
    xy=(nodes_q4[-1], tstar_q4_h[-1]),
    xytext=(550, 50.855),
    fontsize=7.5,
    arrowprops={
        "arrowstyle": "-",
        "color": "#4d5966",
        "lw": 0.7,
    },
)

# （c）BE--BDF 交叉验证
ax = axes[2]
ax.plot(
    be_dt_q3_s[order_q3],
    error_q3_s[order_q3],
    "o-",
    color="#2f6f9f",
    label="问题三：BE-BDF",
)
ax.plot(
    be_dt_q4_s[order_q4],
    error_q4_s[order_q4],
    "s-",
    color="#3f8567",
    label="问题四：BE-BDF",
)
ax.axhline(0, color="#5a656c", lw=0.65)
ax.set_xscale("log", base=2)
ax.set_xticks([2.5, 5, 10, 20], ["2.5", "5", "10", "20"])
ax.set_xlabel("BE 时间步 Δt / s")
ax.set_ylabel("临界时间差 / s")
ax.set_title("BE-BDF 交叉验证", pad=5)
ax.set_ylim(-2, 65)
ax.grid(True, color="#d9dde0", lw=0.5)
ax.legend(frameon=False, loc="upper left", handlelength=1.5)
ax.annotate(
    "最细 BE：\n7.95 s / 6.15 s",
    xy=(2.5, max(error_q3_s[order_q3][0], error_q4_s[order_q4][0])),
    xytext=(4.2, 43),
    fontsize=7.1,
)

# 子图编号
for label, ax in zip(["(a)", "(b)", "(c)"], axes):
    ax.text(
        -0.14,
        1.08,
        label,
        transform=ax.transAxes,
        fontsize=9.5,
        fontweight="bold",
    )

fig.subplots_adjust(
    left=0.08,
    right=0.99,
    bottom=0.22,
    top=0.86,
    wspace=0.42,
)

fig.savefig(OUTPUT, dpi=450, bbox_inches="tight")
plt.close(fig)

print(f"图片已生成：{OUTPUT}")