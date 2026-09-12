# A 题提交代码（按题组织）—— 逐题自包含，便于论文附录整题放置

> 本目录是竞赛提交用的**整洁代码版**，按**问题**组织：顶层就是 `problem1 → problem2 → problem3 → problem4 → sensitivity`（敏感度分析）五个题单元，附录可**一题一题**原样贴入。
> 每题内部再分 `core/`（模型求解核心＝业务）与 `run/`（数据加载·运行编排·结果导出＝管线），保留业务/管线的角色区分。
> 重构只重组目录与 import 路径，**未改动任何建模、离散格式或数值逻辑**；原 `code/problem*` 等开发目录原样保留，可对照回溯。全部单元测试与跨层 import 冒烟均通过（见文末）。

## 目录结构

```
code/submission/
├── problem1/                         问题一
│   ├── core/    solver.py（一维径向守恒 FVM + 隐式 BDF，谐波平均界面 D、C≥0 裁剪）+ test_solver.py
│   └── run/     run_and_verify.py（读附件 → 求解 → 数值复核 → 出表）
├── problem2/                         问题二
│   ├── core/    solver.py + test_solver.py
│   └── run/     run_and_verify.py + export_result2.mjs
├── problem3/                         问题三
│   ├── core/    model.py · fvm.py · solver_bdf.py · solver_be.py + test_solver.py
│   ├── run/     run_and_verify.py + export_result3.mjs
│   └── baselines/ solver.py（原始近似离散基准，供 run 的复现校验 importlib 加载）
├── problem4/                         问题四（主答案 t* = 50.8245 h）
│   ├── core/    model · environment · radius · scenarios · fvm · solver_bdf · solver_be + test_solver.py
│   ├── run/     run_and_verify.py + export_result4.mjs
│   ├── baselines/ L1/solver.py · L2/solver.py（历史基准，供 reproduce_legacy 复现 L1→L3 口径演进）
│   └── analysis/                     加固与对照（随附件提交，可选入附录）
│       ├── bonus_validation/       MMS / Bessel / UQ 加分验证 + 仓库可移植性检查
│       ├── problem4_limitations/   Q4「28.02% 干物质漂移」局限性诊断（5 脚本）
│       └── problem4_mass_closure/  L5 干物质闭合反事实情景（模型形式对照）
├── sensitivity/                      全局敏感性与不确定性量化
│   ├── core/    parameters · morris · pce · sobol · evaluator · cache · radau_crosscheck + test_sensitivity.py
│   └── run/     run_pipeline.py
└── README.md
```

## 论文附录放置指引

按 `problem1 → problem2 → problem3 → problem4 → sensitivity` 顺序，每题**先 `core/`（模型与求解器）后 `run/`（运行与导出）**，逐文件一字不差贴入即可。`problem3/4` 的 `baselines/`、`problem4/analysis/` 属复现基准与加分验证，可按篇幅决定是否入附录（不影响主题目代码的完整性）。

## 运行

附件 `附件/附件1.xlsx`、`附件/附件2.xlsx` 需在位；结果写入仓库 `results/`。代表性命令（完整参数见各脚本 `--help`）：

```powershell
# 问题四主答案（空间网格自适应至收敛，t* = 50.8245 h）
python code/submission/problem4/run/run_and_verify.py `
  --attachment1 附件/附件1.xlsx --attachment2 附件/附件2.xlsx `
  --project-root . --work-dir <仓库外临时目录> --results-dir results/problem4_fvm_bdf

# 全局敏感性与不确定性量化（复用 problem4/core 求解器）
python code/submission/sensitivity/run/run_pipeline.py `
  --attachment1 附件/附件1.xlsx --attachment2 附件/附件2.xlsx `
  --work-dir <仓库外临时目录> --results-dir results/global_sensitivity --workers 4

# 加分验证 + 仓库可移植性检查
python code/submission/problem4/analysis/bonus_validation/run_bonus_validation.py
python code/submission/problem4/analysis/bonus_validation/check_repo_portability.py
```

## 单元测试

```powershell
python -m unittest discover -s code/submission/problem1/core -p "test_*.py"
python -m unittest discover -s code/submission/problem2/core -p "test_*.py"
python -m unittest discover -s code/submission/problem3/core -p "test_*.py"
python -m unittest discover -s code/submission/problem4/core -p "test_*.py"
python -m unittest discover -s code/submission/sensitivity/core -p "test_*.py"
python -m unittest discover -s code/submission/problem4/analysis/bonus_validation -p "test_*.py"
python code/submission/problem4/analysis/problem4_mass_closure/test_closure.py
```

## 依赖

Python 3.12；`numpy` / `scipy` / `pandas` / `openpyxl`。导出 xlsx 的 `.mjs` 需 Node.js 与 `@oai/artifact-tool`（仅各题 `run/` 的 Excel 生成步骤用到）。

## 重构契约（与原始开发目录的对应）

| submission 位置 | 源自 |
| --- | --- |
| `problem1/{core,run}` | `code/problem1_improved` |
| `problem2/{core,run}` | `code/problem2_fvm_bdf` |
| `problem3/{core,run}` · `problem3/baselines` | `code/problem3_fvm_bdf` · `code/problem3`（原始 solver） |
| `problem4/{core,run}` · `problem4/baselines/L1,L2` | `code/problem4_fvm_bdf` · `code/problem4`、`code/problem4_improved_fvmbdf`（L1/L2 solver） |
| `problem4/analysis/*` | `code/bonus_validation`、`code/problem4_limitations`、`code/problem4_mass_closure` |
| `sensitivity/{core,run}` | `code/global_sensitivity` |

- **数值逻辑零改动**：`core/` 下 solver/model/fvm 等逐字节复制，未改任何方程或算法；`core` 内保持同目录 import。
- **仅调整 import 与路径**：`run/` 用 `sys.path` 注入同题 `../core`；`analysis/` 注入 `problem4/core` 与 `problem4/run`（复用 `load_inputs`）；`sensitivity/core/evaluator.py` 注入 `problem4/core`；仓库根定位按新深度取 `parents[4]`（题目录）/`parents[5]`（analysis）；基准 `importlib` 加载路径改指题内 `baselines/`。
- **画图未纳入**：论文配图脚本 `code/paper_figures/` 按约定不参与本次重构，原样保留。

## 验证状态

- `core` 单元测试：problem1 (9) + problem2 (6) + problem3 (10) + problem4 (12) + sensitivity (6) = **43 项全部通过**。
- `run` 五个入口 `--help` 退出码 0，`run → ../core` 注入与跨层 import 链解析成功。
- `analysis`：bonus_validation (5) 通过；problem4_mass_closure `test_closure.py` **6/6 通过**（含实跑 N=201 闭合功能测试）；limitations 的 `problem4/core + problem4/run` 双注入链冒烟通过。
