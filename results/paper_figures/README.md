# 论文正文图 1–5 交付说明（agent_A · 2026-09-12）

认领并执行 @agent_C `2026-09-12T06:50:43Z` 指派的论文画图任务（规格：`discussion/画图建议/论文配图建议（原文）.md`）。
复现命令：`python code/paper_figures/plot_paper_figures.py`（仅读已提交结果 + 本机 `附件/附件1.xlsx、附件2.xlsx`，不新跑物理模型）。
输出：本目录下 `figN_*.png`（600 dpi）与 `figN_*.pdf`（矢量，供论文插入）。图内标题/坐标/图例/色条/注释全中文。

## 图清单与数据来源

| 文件 | 图题 | 数据来源（只读，未改动） |
|---|---|---|
| fig1_problem1_radial | 图1 问题一预热阶段药材温度与水分浓度的径向演化 | results/problem1_improved/result1.xlsx（t=100/600/1200/1800 s） |
| fig2_problem2_heatmap | 图2 变物性热湿耦合条件下温度与水分浓度的时空演化 | results/problem2_fvm_bdf/result2.xlsx（T、C 双热力图+等值线） |
| fig3_problem3_event | 图3 固定半径条件下水分浓度演化及全域达标时刻 | results/problem3_fvm_bdf/result3.xlsx + verification.json（t\*=57.172706 h、首个60 s达标 57.183333 h） |
| fig4_problem4_moving_boundary | 图4 半径收缩条件下水分浓度演化及收缩作用对照 | results/problem4_fvm_bdf/result4.xlsx + verification.json（shrinkage_ablation）；R(t) 经 code/problem4_fvm_bdf/run_and_verify.load_inputs 读附件2 |
| fig5_pce_sobol | 图5 PCE 代理模型预测精度及干燥时间的 Sobol 全局敏感性 | results/global_sensitivity/{pce_validation,high_fidelity_checks,sobol_indices}.json |

## 口径区分（与 C 的硬性要求一致）
- 50.8245 h = 问题四主答案；129.0944 h = 固定半径反事实对照（消融，非答案）；
- Euler 空间坐标模型 52.3842 h = 仅模型形式敏感性对照；质量闭合 60.7443 h = 替代闭合情景；二者均不作并列答案（图4(b) 内已加口径框）。
- 图3 中连续临界时间 57.172706 h 与首个 60 s 离散达标时刻 57.183333 h 分开标注。
- 图5 的 Sobol 排序依赖预设独立均匀工程扰动范围，不表述为观测统计置信结论。

## 论文插入位置建议（供持 files 锁者执行，本轮不改 tex）
- 图1 → 问题一"模型建立与求解"结果段，替换/合并现有两幅单场图；
- 图2 → 问题二结果段首图（该问当前零插图）；
- 图3 → 问题三结果段，配合 t\*=57.1727 h 的确定过程；
- 图4 → 问题四结果段，(b) 的口径框文字可并入正文"结果使用建议与适用边界"；
- 图5 → 仅当全局敏感性进入正文时插入，否则转附录；
- 插入时补"如图 X 所示"图文互引；Bessel/MMS/网格收敛等验证图按 C 意见不放正文（可附录）。

## 验收自检
- 5 幅图均渲染成功且中文无缺字（视觉逐幅自检）；数值标注与 verification.json / sensitivity 报告逐位一致；
- 未修改任何既有 code/results/files 内容；仅新增 code/paper_figures/ 与本目录。
