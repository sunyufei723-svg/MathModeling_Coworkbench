# 论文插图方案（提案）· by agent_A

> **性质**：提案，非最终分工。@agent_B @agent_C 请先在各自 `requests/agent_<你>.md` 确认/调整认领与优先级，再动手生成图片。
> **目标文件**：`files/final/A题完整论文.tex`（成品论文）。**当前全文仅问题一有 2 张插图，问题二/三/四、模型检验、全局敏感性全为纯表格+文字，零插图**——对国奖风格论文是明显短板（参照 `files/raw/` 往届国奖论文图文密集、频繁「如图 X 所示」）。
> **红线**：插图只增不改——所有既有数字/公式/表格/结论一字不动；图数据一律取自已提交的 `results/` 真值，不得新造数。

---

## 一、现状盘点（论文浮动体全清单）

| 章 | 位置 | 现有浮动体 | 插图数 |
|---|---|---|---|
| 符号说明 | line114 | 表·主要符号说明 | 0 |
| 问题一 | line242/248/266/284/291 | 算法·求解流程 + 表q1-temp + 表q1-moist + **图·温度径向剖面** + **图·水分径向剖面** | **2** ✅ |
| 问题二 | line355/363/380 | 算法·BDF推进 + 表q2-temp + 表q2-moist | 0 ❌ |
| 问题三 | line431/445 | 算法·达标停机 + 表q3-moist | 0 ❌ |
| 问题四 | line526/538/578 | 算法·移动边界 + 表q4-moist + 表7两坐标对照 | 0 ❌ |
| 模型检验与稳定性 | line565-603 | （无浮动体） | 0 ❌ |
| 模型评价 | line604-634 | （无浮动体） | 0 ❌ |

**已有作图资产**：仅 `results/problem1/figures/` 下 2 张（温度/水分径向剖面，png+pdf），由 `code/problem1/plot_problem1_figures.R`（R+ggplot2）生成。

---

## 二、拟插入图片清单（分三档优先级）

> 图号为提案简记；插入后由 LaTeX 自动编号，正文用 `如图\ref{fig:...}所示` 引用。owner 按「谁的 results 数据谁作图」划分（最熟数据结构、免跨 agent 理解 schema）。

### Tier 1 · 核心必补（填补 P2/P3/P4 零图空白，6 张）

| 简记 | 章节位置 | 内容 | 图型 | 数据源 | owner | 建议文件名 |
|---|---|---|---|---|---|---|
| 图2-1 | 问题二·表3/4 后 | t=0.5/1.5/3.0 h 温度 & 水分径向剖面（双 panel） | 折线 | `results/problem2_fvm_bdf/result2.xlsx` | **C** | `problem2_radial_profiles.pdf` |
| 图3-1 | 问题三·表5 后 | max(C)(t) 衰减曲线 + 0.15 阈值水平线 + t\*=57.17 h 竖直标记 | 折线+标注 | `results/problem3_fvm_bdf/verification.json`（时序） | **C** | `problem3_maxC_decay.pdf` |
| 图3-2 | 问题三 | 水分径向剖面演化（t=0,6,…,54,57.17 h 多条），展示干燥前沿向中心推进 | 多折线 | `results/problem3_fvm_bdf/result3.xlsx` | **C** | `problem3_moisture_profiles.pdf` |
| 图4-1 | 问题四·表6 前 | R(t) 半径收缩曲线（2.0→1.198 cm，0–72 h），移动边界输入 | 折线 | 附件2 / `problem4_fvm_bdf/verification.json` | **C** | `problem4_radius_shrinkage.pdf` |
| 图4-2 | 问题四·表6 后 | max(C)(t) 对比：问题三(固定半径 57.17 h) vs 问题四(收缩 50.82 h) + 0.15 阈值，直观示「收缩加快后期达标 Δ≈6.35 h」 | 双折线 | p3+p4 `verification.json` | **C**（跨两问） | `problem4_maxC_vs_q3.pdf` |
| 图5-1 | 模型检验章 | 网格收敛 log-log（Δt\* 或场差 vs Δr，标观察阶 p=2.30 + Richardson 外推） | log-log 折线 | p3/p4 `verification.json` 网格序列 | **C** | `verify_mesh_convergence.pdf` |

### Tier 2 · 强化严谨性/局限（6 张，强烈建议）

| 简记 | 章节位置 | 内容 | 图型 | 数据源 | owner | 建议文件名 |
|---|---|---|---|---|---|---|
| 图2-2 | 问题二 | 中心 vs 表面 T(t)、C(t) 演化（0–3 h），示 T 趋近烘房温度而 C 保持内外梯度 | 双 panel 折线 | `problem2_fvm_bdf` 时序 | **C** | `problem2_center_surface_evo.pdf` |
| 图4-3 | 模型评价·干物质局限段(line619/622附近) | κ(t) 干物质诊断曲线（κ=G·S，28.02% 谷值@7 h、κ_min=0.7198、终点 0.8903），支撑 line622-628 决策F 局限论述 | 折线+标注 | `results/problem4_mass_closure/verification.json` + `_work/n3201.json` | **A** | `problem4_drymass_kappa.pdf` |
| 图5-2 | 模型检验章 | 双求解器互证（BDF vs backward-Euler+Picard，max(C)(t) 叠加或差值，差 7.95 s/6.15 s） | 折线 | p3/p4 `verification.json` | **C** | `verify_dual_solver.pdf` |
| 图5-3 | 模型检验章·边界敏感性段 | 边界敏感性区间条图（Q3 53.6–61.1 h、Q4 47.7–54.3 h、+h_m 扰动、+数据驱动延拓） | 区间条/误差棒 | p3/p4 `boundary_sensitivity.md` | **C** | `verify_boundary_sensitivity.pdf` |
| 图1-3 | 问题一（可选，锦上添花） | T/C 中心-表面时间演化，或 r–t 时空云图（热力图）示「表面先响应、中心滞后」 | 折线/热力图 | `results/problem1/result1.xlsx` 全网格 | **A** | `problem1_spacetime_or_evo.pdf` |
| 图2-3 | 问题二（可选） | 附录3 物性 ρ,c_p,k,D 随 C 变化曲线，展示非线性耦合来源 | 多 panel 折线 | 附录3 公式（解析） | **C 或 A** | `problem2_property_vs_C.pdf` |

### Tier 3 · UQ 加分项（4 张，**条件：先决定正文是否新增 UQ 小节，见 §五待决问题**）

| 简记 | 章节位置 | 内容 | 图型 | 数据源 | owner | 建议文件名 |
|---|---|---|---|---|---|---|
| 图6-1 | 新 UQ 小节(待定) | Sobol 一阶 S_i + 总效应 S_Ti 条形图（5 参数，activation_temperature 主导 S_i=0.940） | 条形 | `results/global_sensitivity/sobol_indices.json` | **B** | `uq_sobol_indices.pdf` |
| 图6-2 | 新 UQ 小节 | Morris 筛选散点（μ\* vs σ，9 参数，标出入选 PCE 的 5 个） | 散点 | `results/global_sensitivity/morris_results.json` | **B** | `uq_morris_screening.pdf` |
| 图6-3 | 新 UQ 小节 | PCE 代理 vs N3201 高保真 PDE 校验散点（Q²=0.9999998、RMSE=0.0069 h）+ 45° 线 | 散点 | `global_sensitivity/pce_validation.json` + `high_fidelity_checks.json` | **B** | `uq_pce_validation.pdf` |
| 图6-4 | 新 UQ 小节 / 检验章 | Bessel 本征解 + MMS 制造解收敛验证（误差 vs N，log-log，阶≈2） | log-log 折线 | `results/bonus_validation/` | **B** | `validation_bessel_mms.pdf` |

---

## 三、作图工具链与风格规范（与既有 2 图统一）

- **首选 R + ggplot2**，模板 `code/problem1/plot_problem1_figures.R`（已验证可跑、读 xlsx→出 png+pdf）。若 owner 的数据管线是 Python 更顺手，可用 matplotlib，但**必须匹配下列视觉规范**以保证全文风格一致。
- **视觉规范**（照抄模板）：`theme_bw(base_size=10, base_family="Times New Roman")`；Okabe-Ito 色盲友好配色（`#0072B2` 蓝 / `#E69F00` 橙 / `#009E73` 绿 / `#D55E00` 朱红 / …）；多曲线用不同 colour+linetype 双编码；白底；**图内标签用英文**（如 `Distance from center / cm`、`Moisture content / kg kg^-1`），与既有 2 图一致；`\caption` 用中文。
- **输出**：每张同时存 `.png`(600 dpi) + `.pdf`(cairo_pdf)，单栏图 6.7×3.8 in，双 panel 可加宽；均落 `results/problemX/figures/`。
- **命名**：`problemX_<snake_desc>.pdf`（沿用 `problem1_temperature_radial_profiles` 风格）。
- **脚本位置**：`code/problemX/plot_problemX_figures.<R|py>`，只读 `results/` 数据、不改任何现有代码/结果。
- **多 panel**：优先在作图脚本内用 ggplot facet / patchwork（或 matplotlib subplot）合成**单个 pdf**，tex 里一条 `\includegraphics` 引入，避免 subfigure 复杂度。

---

## 四、插入机制（由 A 统一在 files 锁下完成）

- 图生成方（B/C/A）先把**脚本入 `code/`、图入 `results/problemX/figures/`** 并各自提交（走 code+results 锁）。
- **A 最后统一插入 tex**（持 files 锁），套用既有范式：
  ```latex
  \begin{figure}[H]
    \centering
    \includegraphics[width=0.92\textwidth]{../../results/problemX/figures/xxx.pdf}
    \caption{中文说明（国奖风格：陈述图揭示了什么规律，而非仅"这是XX图"）。}
    \label{fig:qX-xxx}
  \end{figure}
  ```
- 在相关正文处补 `如图\ref{fig:qX-xxx}所示` 引用（往届国奖高频图文互引），把图织进叙述。
- 插入后 XeLaTeX 二次编译，按四指标验收（0 error / 0 Overfull / 0 undefined ref / 页数）；`width=0.92\textwidth` 一般不溢出，但双 panel 宽图需查 Overfull（见 working-rules latex-compile）。

---

## 五、待决问题（请 @agent_B @agent_C 及队员拍板）

1. **UQ 正文缺口（重要）**：`results/global_sensitivity/` 已有完整 Sobol/Morris/PCE 结果、`results/bonus_validation/` 已有 Bessel/MMS 验证，**但论文正文 line634「模型改进方向」仍把「全局敏感性分析(Sobol/Morris)」列为未来工作**。二者矛盾。选项：
   - (a) 新增一个「全局敏感性与不确定度量化」小节，把 B 的结果写进正文 + 插图6-1~6-4（内容扩充，B 主导文字、A 插入，需 files 锁），并把 line634 该条从「改进方向」移除/改写；
   - (b) 暂不整合，UQ 仅作附加材料，本轮跳过 Tier 3 图。
   - **请 B 表态**（数据是 B 的），并请队员定夺是否扩正文。
2. **分工确认**：Tier 1/2 中划给 C 的 8 张（P2/P3/P4 场量 + 检验章收敛/双求解器/边界敏感）是否由 C 认领？划给 A 的 2 张（图4-3 κ 诊断、图1-3 可选）+ 全部 tex 插入由 A 负责，请 B/C 知悉。
3. **图数量与篇幅**：Tier1(6)+Tier2(6)=12 张，预计论文从 22 页增至约 28–30 页。是否符合队伍预期？Tier 3 视问题 1 决定。
4. **锁时序**：`results.lock`、`code.lock` 均为**粗粒度**（覆盖整个目录），B/C/A 生成图时**不能同时持锁**，需串行。建议每方一次性把本方所有图（脚本+图片）生成并提交完再释放，减少交接。A 的 tex 插入放最后（依赖图已入库）。

---

## 六、建议执行时序

1. **A（本轮）**：写此提案 + 板 @B@C，释放 discussion 锁。← 当前
2. **B/C**：各自板确认认领 + 对 §五问题 1/2/3 表态。
3. **C**：持 code+results 锁 → 生成 Tier1/2 划归 C 的图（脚本+png+pdf）→ 提交 → 释放。
4. **B**：持 code+results 锁 → 生成 Tier3 UQ 图（若 §五问题1 选 a）→ 提交 → 释放。
5. **A**：持 code+results 锁 → 生成图4-3 κ 诊断 + 图1-3（可选）→ 提交 → 释放；再持 files 锁 → 统一插入全部图 + 补「如图 X 所示」引用 + 编译验收 → 释放。

> 有异议或更优分工，请在本方 `requests/agent_<你>.md` 回复；我会据此更新本提案。
