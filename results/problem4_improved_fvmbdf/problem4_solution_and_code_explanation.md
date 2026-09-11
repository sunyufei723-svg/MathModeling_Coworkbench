# A题问题4改进副本说明（不改源文件）

本目录是问题4的独立改进副本，源文件来自 `E:\MathModeling_Coworkbench\code\problem4\`，但本次没有改动原仓库源文件。改进代码位于：

- `code/problem4_improved_fvmbdf/solver.py`
- `code/problem4_improved_fvmbdf/run_problem4.py`
- `code/problem4_improved_fvmbdf/test_solver.py`

## 1. 为什么问题4可以继续用 FVM-BDF

可以继续用，但论文和代码里应说得更准确：当前方法是“守恒有限体积法（FVM）+ 一阶后向差分 BDF1（backward Euler）+ Picard 耦合迭代”。它不是自适应高阶 BDF 求解器，但对本题这种径向扩散、Robin 边界、物性随含水率和温度变化的半离散系统，BDF1 的全隐式格式稳定、可解释、也便于和问题2/3保持统一。

因此问题4保留问题2/3的总体数值框架：固定 ξ 网格、每步全隐式、三对角求解、Picard 联立温度和含水率。移动边界通过 front-fixing 写入有效系数 `cond / R(t)^2` 和 `transfer / R(t)`。

## 2. 本次结合 A 留言板后的改进

1. `SolverConfig().xi_points` 默认改为 201，和生产运行脚本 `--xi-points 201` 保持一致。
2. 水分扩散项的界面扩散系数改为谐波平均。对 `D(C,T)` 跨数量级变化的后期干燥过程，谐波平均比算术平均更保守，能减少界面通量被高扩散一侧过度抬高的问题。
3. 温度传导仍保留算术平均，避免把这次改动扩大到不必要范围。
4. 含水率仍做非负裁剪，防止极端迭代下 `C<0` 进入指数物性公式。
5. 运行脚本适配仓库标准结构，输出会写到 `results/problem4_improved_fvmbdf/`，不会覆盖原 `results/problem4/`。

## 3. 和问题2思路保持一致的部分

- 附件路径支持显式传入 `--attachment1` 和 `--attachment2`。
- 输出 Excel 时，时间列格式为整数，水分数值列格式为 `0.0000`。
- 仍输出 `result4.xlsx` 和论文表格 `problem4_tables.md`。
- 仍用单元测试保护附件插值、附录4物性公式、达标停机、移动边界收缩加速、D=0时物质坐标守恒等关键假设。

## 4. 复现方式

在有附件 Excel 的情况下运行：

```powershell
cd E:\MathModeling_Coworkbench\code\problem4_improved_fvmbdf
py run_problem4.py --attachment1 "附件1.xlsx的路径" --attachment2 "附件2.xlsx的路径" --xi-points 201 --dt 10
```

运行测试：

```powershell
cd E:\MathModeling_Coworkbench\code\problem4_improved_fvmbdf
py -m unittest -v
```

## 5. 当前验证状态

已通过 13 条单元测试，包括新增的三项：

- 默认生产网格为 201 点；
- 谐波平均确实限制跳跃界面的扩散通量；
- 独立副本运行脚本只向 `results/problem4_improved_fvmbdf/` 写结果。

**【2026-09-11T12:32Z agent_A 更新：改进版结果已真跑并重新生成】** 本机 `附件/` 齐全（各机器在项目目录各自存有附件副本；gitignore 只表示「不入库」，不表示「别人拿不到」），agent_A 已用改进算法真跑并覆盖生成本目录 `result4.xlsx` 与 `problem4_tables.md`——**不再是原问题4的基线复制件**。网格加密 201/401/801 收敛（401↔801 相对变化 1.6e-4 < 1e-3）：**生产口径 xi=801，t\*=50.7944 h（收敛≈50.79 h）**；xi=201 给 50.8639 h（未收敛，勿用作论文定值）。完整阶梯 / Richardson / GCI / 算术vs调和干净对照见同目录 `mesh_convergence_by_A.md`。另注：上文「13 条单元测试通过」是在 C 开发机（文件夹名恰好匹配 `test_solver.py:31` 硬编码的 `MathModeling_Coworkbench_push_tmp2`）下成立；换任何机器因该行硬编码仓库名会是 12/13（复核必改1），建议改为仓库名无关断言。
