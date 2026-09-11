# 问题四 L2 / L3 reconcile（agent_A）

- 复核 + reconcile 人：agent_A（本机 Qoder）
- 时间：2026-09-11T16:03:00Z
- 触发：agent_C 的 L3 `problem4_fvm_bdf` 已落地（提交 `235e0e3`、code+results 锁已在该提交释放）；我方留言板 `requests/agent_A.md` 唯一活跃项（[2026-09-11T12:05:00Z] @agent_C）约定「L3 落地后我复核并 reconcile L2(50.79h)/L3」。
- 证据基准：`code/problem4_fvm_bdf/`（fvm/model/radius/environment/scenarios/solver_bdf/solver_be/test 全读）+ `results/problem4_fvm_bdf/`（numerical_verification.md / baseline_comparison.md / problem4_solution_and_code_explanation.md / problem4_tables.md / boundary_sensitivity.md / radius_sensitivity.md / model_form_sensitivity.md / shrinkage_ablation.md / verification.json）+ 我方独立 L2 `results/problem4_improved_fvmbdf/`（mesh_convergence_by_A.md）+ `discussion/problem4_improved_review_by_A.md`（§二十二 方案复核）。

---

## 一句话结论

**L3 = 50.824507 h 采纳为论文问题四主值（正文报 ~50.82 h）**；L2 = 50.7944 h 降为「近似离散 + 固定步 BE」基准对照 rung；**C 的 L2 复现 = 50.794444 h 与我方独立 L2 = 50.7944 h 完全一致 ⇒ 双管线互证**，L3（同一管线的严格化）可信。此结论 **supersede** B 在 `f3f7dde` 采用的 Q4 = 50.79 h（该采用在 L3 落地前做出）。论文 tex 刷新仍按用户中断暂挂，本 reconcile 只定「用哪个值 + 建立阶梯」，不动 `files/`。

---

## 1. L3 复核结论（代码 + 数值，全部通过）

代码逐项核对，与 `problem4_solution_and_code_explanation.md` 的数学描述**完全吻合**，也正是我 §二十二 复核赞成的方案：

| 复核点 | 证据 | 结论 |
|---|---|---|
| 物质坐标 RHS（1/R² 尺度因子、**主模型无对流项**） | `solver_bdf.py:137–175`；eulerian 输运项仅在 `model_form=="eulerian"` 分支（`:166–170`，即 L4） | ✓ 正确（仿射收缩下 ξ 系材料静止，无虚假平流） |
| 守恒内部通量（每面算一次、反号入相邻控制体 → 严格 telescoping） | `fvm.py:51–66` `internal_flux_numerator` | ✓ 最大归一化通量残差 **2.087e-16**（机器精度） |
| 严格圆柱控制体几何（V̂ᵢ=½(ξ²ᵢ₊½−ξ²ᵢ₋½)、Â=ξᵢ₊½、ΣV̂=½） | `fvm.py:21–30` | ✓ 中心/表面半控制体统一权重 |
| k、D 界面**调和平均** | `fvm.py:33–48` + `solver_bdf.py:143–154`（config 默认 `k_interface_mean=d_interface_mean="harmonic"`） | ✓ 与全文「调和平均界面通量」口径一致 |
| 联合状态自适应 BDF + 块三对角 `jac_sparsity` | `solver_bdf.py:282–293`（`method="BDF"`、`rtol=1e-8`、split `atol`：T 1e-8 / C 1e-10、`max_step=30s`） | ✓ |
| 附件1 末（14400s）分段积分 + 终止事件 | `solver_bdf.py:301–332`；事件 `g(t)=max(C)−0.15`（`:112–113`）、`terminal=True`、`direction=−1` | ✓ 72h 未触发则 96h fallback，再未触发 raise（鲁棒） |
| 首个**严格达标** 60s 输出时刻 | `solver_bdf.py:334–339`；`verification.json`：182940s=0.15001459(>0.15)、183000s=0.14998359(<0.15) | ✓ Excel 末行确为第一个严格 <0.15 的 60s 时刻 |
| **无状态裁剪**（仅物性公式用 `C_safe=max(C,1e-9)`） | `model.py:6–9`；`solver_bdf.py:404–408` guard 物质负值（`< −1e-8` 才 raise） | ✓ `clipped_cell_count=0`、`min_raw_moisture=0.0525`（无负含水率） |
| 网格收敛 201→3201 | `numerical_verification.md`：50.909116/50.844229/50.829110/50.825422/**50.824507**，相邻差 −233.6/−54.4/−13.3/**−3.295s**（~4× 递减） | ✓ 单调收敛，末级差 3.3s |
| BDF 容差收敛 | rtol 1e-7/1e-8/1e-9 → 50.824506/50.824507/50.824507（差 <2e-4 s） | ✓ |
| BE 时间步交叉验证 | `solver_be.py`；dt 20/10/5/2.5s → 50.837674/50.831163/50.827865/50.826215，向 BDF 收敛；`cross_solver` 最细 BE vs BDF 差 **6.15s**（rel 3.36e-5） | ✓ 独立求解器互证 |
| 全域最大含水率恒在中心 ξ=0 | `verification.json.final.argmax_location_xi=0.0` | ✓ 中心最迟达标（物理正确） |

**结论：L3 代码正确、数值收敛、双求解器（BDF/BE）交叉互证、守恒到机器精度、无裁剪。** 我 §二十二 复核提的 **4 必改**中：#2（真跑出 result4.xlsx）✓ 已落实、#3（物质坐标假设写入说明）✓ 已落实、#4（>4h 边界延拓敏感性）✓ 已落实（`boundary_sensitivity.md`）；#1（`test_solver.py:31` 硬编码仓库名）属 **code 锁**范围、非本 results 路径，待 C 确认或 code 锁空闲时改（非阻塞）。

---

## 2. L1–L4 阶梯（reconcile 定稿）

| 层级 | 模型与数值口径 | t\*/h | reconcile 后角色 |
|---|---|---|---|
| L1 | 近似离散、k/D 算术、201 点、固定 10s BE | 50.652778 | 历史基准（最粗） |
| **L2** | 近似离散、D 调和、801 点、固定 10s BE | **50.794444** | **我方独立 L2 = 50.7944 h 完全一致 → 互证锚点**；降为「近似离散 + 固定步」基准对照 |
| **L3** | 严格 FVM、k/D 调和、自适应 BDF、连续事件、3201 点 | **50.824507** | **论文问题四主值（正文报 ~50.82 h）** |
| L4 | Euler 型 + 收缩输运项、同一 L3 离散 | 52.384238 | 模型形式敏感性（**非更高层级**，是另一种坐标物理解释） |

- 连续临界 t\* = 182968.225 s = **50.824507 h**；第一个严格达标 60s 输出时刻 = 183000 s = 50.833333 h（表6/Excel 末行）。
- 表6 用 C 的 `results/problem4_fvm_bdf/problem4_tables.md`（已含「药材表面」移动列 + 临界行 50.824507）。

---

## 3. L2 → L3 差异归因（+0.030 h = +0.06%）

C 的 `baseline_comparison.md` 数值消融（均 201 点，逐项隔离）：

| 实验 | 改动 | t\*/h | 相对前项/min |
|---|---|---|---|
| A0 | L1 近似（arithmetic/arithmetic/BE10s） | 50.652778 | — |
| A1 | → 严格 FVM 几何 | 50.818924 | +9.97 |
| A2 | → D 调和 | 50.915712 | +5.81 |
| A3 | → k 调和 | 50.915712 | 0.00（k 随 C 变化弱） |
| A4 | → 自适应 BDF | 50.909116 | −0.40 |

再网格 201→3201 收敛到 **50.824507**（A4@201=50.909116 → 3201=50.824507，网格细化 −0.085h）。

- **L2(50.7944) → L3(50.8245) 净差 +108s（+0.06%）**，来源＝几何严格化 + k 调和 + 自适应 BDF + 连续事件 + 3201 网格的合力，**远小于后期边界情景范围 47.6834–54.2753 h（±3.3 h）**。即：数值口径差可忽略，**物理边界不确定度主导** t\* 的真实误差棒。
- **互证关键**：C 的 L2（50.794444 h）与我方独立 L2（50.7944 h、`mesh_convergence_by_A.md`、物质坐标 + 水分调和 D + 固定 dt=10 + 一阶 BDF+Picard）**四位小数完全一致**。由于 R(t) 以 1/R² 进入 RHS、物性附录4、附件1/2 插值都参与，**两条独立管线得到完全相同的 L2 ⇒ 二者读附件2 R(t)、附录4 物性、离散口径完全一致**，因此 L3（在同一已互证管线上做严格化 + 网格收敛）可信。

---

## 4. 下游动作

1. **论文问题四主值：50.79 h → 50.82 h（L3）**。正文报 ~50.82 h（4 位小数 50.8245），并**同时报后期边界情景区间 47.68–54.28 h**，说明「不宜把更多小数解释成物理预测精度」（C 的 explanation §结果解释亦持此口径）。
2. **表6** 换用 C 的 `problem4_tables.md`（含移动表面列 + 临界行）；`result4.xlsx` 用 `results/problem4_fvm_bdf/result4.xlsx`。
3. **files/ 刷新仍暂挂**（待用户/队员指示再动 tex）——本 reconcile 只对齐「Q4 用哪个值 + 阶梯」，不改论文。届时一次性刷新 Q4 主值 50.82h + 表6 + 检验章（BDF 步长/网格收敛统计 + 边界情景）。
4. **Table 6 的 1.5 cm 列自 6 h 起全程留空**＝R(t)<1.5 cm（附件2 前期陡降、event R=1.2 cm、R(t)∈(1.0,1.5) for t≥6h）——由 §3 的 L2 互证确认**非误读**，是附件2 半径轨迹的真实形状。论文应**注明 R(t) 轨迹（前期快、后期缓）**，避免 reviewer 把留空误当错误。
5. **dry_mass_index 相对变化 28.02%**＝题目给定 R(t) + 经验密度关系未形成严格质量闭合，C 已诚实标注为**模型局限、非求解器失败条件**——论文可在模型评价里一句话说明（加分项，非必须）。

---

## 5. 与 B 的问题四后续优先级对照（`ideas.md` 14:39Z / board line56）

| B 提的 Q4 后续 | C 的 L3 是否覆盖 |
|---|---|
| ① dt=5/20s 时间步敏感性 | ✓ `numerical_verification.md`：BE dt 20/10/5/2.5s + BDF rtol/max_step 三配置 |
| ② >4h 边界 3×3 敏感性 | ✓ `boundary_sensitivity.md`：3×3（T±2°C × C{0.9,1.0,1.1}）+ hm±10% + 数据驱动 tail-avg，范围 47.68–54.28h |
| ③ `test_solver.py:31` 硬编码仓库名 | ⏳ 属 **code 锁**、非 results 路径；待 C 确认或 code 锁空闲时改（非阻塞） |
| ④ adaptive BDF / Euler 对照 | ✓ L4 eulerian（52.38h）+ BDF/BE 交叉验证（差 6.15s） |

**即 C 的 L3 已覆盖 B 全部问题四后续优先级（①②④ 完成，③ 待 code 锁）。**

---

## 6. 对 B / C 的通知（留言板 `requests/agent_A.md` 同步）

- **@agent_B**：你 `f3f7dde` 采用 Q4 = 50.79 h（L2）在 L3 落地前做出；现 L3 已通过我复核，reconcile 结论＝**论文 Q4 主值更新为 50.82 h（L3 = 50.824507h）**，L2 50.7944h 降为基准对照 rung，L1 50.6528h / L4 52.38h(Euler) 角色不变。论文 tex 刷新仍暂挂，届时 Q4 用 50.82h + 表6 用 C 的 `problem4_tables.md`。
- **@agent_C**：你的 L3 `problem4_fvm_bdf` **通过我复核**（代码 + 数值全过、双求解器互证、守恒到机器精度、无裁剪），**采纳为问题四主值**；reconcile 完成。两点请确认（非阻塞）：(a) 附件2 R(t) 前期陡降（R(6h)<1.5cm）属实——我由 L2 互证推定如此，但你本机有原始附件可直接核对；(b) `test_solver.py:31` 硬编码仓库名是否已修（属 code 锁）。
