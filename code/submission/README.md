# A 题提交代码（重构版）—— 业务 / 管线 / 分析 三层组织

> 本目录是竞赛提交用的**整洁代码版**，由仓库 `code/` 下分散的开发目录重构而来。
> 重构只重组目录结构与 import 路径，**未改动任何建模、离散格式或数值逻辑**；原
> `code/problem*`、`code/global_sensitivity` 等开发目录**原样保留**，可对照回溯。
> 全部单元测试与跨层 import 冒烟均已通过（见文末「验证状态」）。

## 目录结构

```
code/submission/
├── business/          业务模块：模型方程 + 数值求解核心（可复用的“引擎”）
│   ├── problem1/        一维径向守恒 FVM + 隐式 BDF（谐波平均界面 D、C≥0 裁剪）
│   ├── problem2/        问题二求解器
│   ├── problem3/        问题三 model / fvm / solver_bdf / solver_be
│   ├── problem4/        物质坐标移动边界严格 FVM+BDF（主答案 t* = 50.8245 h）
│   └── sensitivity/     全局敏感性：Morris / PCE / Sobol / Radau 交叉验证
├── pipeline/          管线模块：数据加载 → 运行编排 → 数值验证 → 结果导出
│   ├── problem1 … problem4/   各问 run_and_verify.py（+ 导出 xlsx 的 export_*.mjs）
│   └── sensitivity/           run_pipeline.py 敏感性全流程编排
├── analysis/          分析与对照：加固与佐证，不产生主答案
│   ├── bonus_validation/       MMS / Bessel / UQ 加分验证 + 仓库可移植性检查
│   ├── problem4_limitations/   Q4「28.02% 干物质漂移」局限性诊断脚本
│   └── problem4_mass_closure/  L5 干物质闭合反事实情景（模型形式对照）
└── baselines/         复现依赖的历史基准求解器（只读，供 L1/L2 口径对照复现）
    ├── problem3/        问题三原始近似离散 solver
    ├── problem4_L1/     问题四 L1 基准
    └── problem4_L2/     问题四 L2 基准
```

## 三层职责

- **business（业务）**：物理模型（附录物性公式）、空间离散（有限体积几何与通量）、时间推进求解器。纯计算、不含 IO 与编排，可被 pipeline 与 analysis 复用。各问 `test_solver.py` 随业务模块同目录放置（`sys.path` 自足）。
- **pipeline（管线）**：读附件 → 调 business 求解 → 数值验证（网格/时间步无关性、交叉验证、消融）→ 写 `results/` 表格与工作簿。是“跑一次复现论文结果”的入口。
- **analysis（分析）**：加分验证、局限性诊断、反事实情景对照；只读复用 business/pipeline，不改其任何文件。
- **baselines（基准）**：被 pipeline 复现校验用 `importlib` 动态加载的历史版本 solver，只读，确保 L1→L3 口径演进可复现。

## 运行

附件 `附件/附件1.xlsx`、`附件/附件2.xlsx` 需在位；结果写入仓库 `results/`。代表性命令如下，完整参数见各脚本 `--help`：

```powershell
# 问题四主答案（空间网格自适应至收敛，t* = 50.8245 h）
python code/submission/pipeline/problem4/run_and_verify.py `
  --attachment1 附件/附件1.xlsx --attachment2 附件/附件2.xlsx `
  --project-root . --work-dir <仓库外临时目录> --results-dir results/problem4_fvm_bdf

# 全局敏感性与不确定性量化
python code/submission/pipeline/sensitivity/run_pipeline.py `
  --attachment1 附件/附件1.xlsx --attachment2 附件/附件2.xlsx `
  --work-dir <仓库外临时目录> --results-dir results/global_sensitivity --workers 4

# 加分验证 + 仓库可移植性检查
python code/submission/analysis/bonus_validation/run_bonus_validation.py
python code/submission/analysis/bonus_validation/check_repo_portability.py

# Q4 局限性上界论证（模型无关）
python code/submission/analysis/problem4_limitations/upper_bound_proof.py
```

## 单元测试

```powershell
python -m unittest discover -s code/submission/business/problem1 -p "test_*.py"
python -m unittest discover -s code/submission/business/problem2 -p "test_*.py"
python -m unittest discover -s code/submission/business/problem3 -p "test_*.py"
python -m unittest discover -s code/submission/business/problem4 -p "test_*.py"
python -m unittest discover -s code/submission/business/sensitivity -p "test_*.py"
python -m unittest discover -s code/submission/analysis/bonus_validation -p "test_*.py"
python code/submission/analysis/problem4_mass_closure/test_closure.py
```

## 依赖

Python 3.12；`numpy` / `scipy` / `pandas` / `openpyxl`。导出 xlsx 的 `.mjs` 需 Node.js 与 `@oai/artifact-tool`（仅 pipeline 的 Excel 生成步骤用到）。

## 重构契约（与原始开发目录的对应）

| submission 位置 | 源自 |
| --- | --- |
| `business/problem1` | `code/problem1_improved`（solver） |
| `business/problem2` | `code/problem2_fvm_bdf`（solver） |
| `business/problem3` | `code/problem3_fvm_bdf`（model / fvm / solver_bdf / solver_be） |
| `business/problem4` | `code/problem4_fvm_bdf`（model / environment / radius / scenarios / fvm / solver_bdf / solver_be） |
| `business/sensitivity` | `code/global_sensitivity`（parameters / morris / pce / sobol / evaluator / cache / radau_crosscheck） |
| `pipeline/*` | 各目录的 `run_and_verify.py` / `run_pipeline.py` / `export_*.mjs` |
| `analysis/bonus_validation` | `code/bonus_validation` |
| `analysis/problem4_limitations` | `code/problem4_limitations` |
| `analysis/problem4_mass_closure` | `code/problem4_mass_closure` |
| `baselines/problem3, problem4_L1, problem4_L2` | `code/problem3`、`code/problem4`、`code/problem4_improved_fvmbdf` 的 `solver.py` |

- **数值逻辑零改动**：business 下的 solver / model / fvm 等文件逐字节复制，未改任何方程或算法。
- **仅调整 import 与路径**：管线/分析脚本改用 `sys.path` 注入对应 `business/`（analysis 另注入 `pipeline/problem4` 以复用 `load_inputs`）；仓库根定位由 `parents[2]` 改为 `parents[4]`；历史基准的 `importlib` 加载路径改指 `baselines/`。
- **画图未纳入**：论文配图脚本 `code/paper_figures/` 按约定不参与本次重构，原样保留。

## 验证状态

- business 单元测试：problem1 (9) + problem2 (6) + problem3 (10) + problem4 (12) + sensitivity (6) = **43 项全部通过**。
- pipeline 五个入口 `--help` 退出码 0，跨层 import 链解析成功。
- analysis：bonus_validation (5) 通过；problem4_mass_closure `test_closure.py` **6/6 通过**（含实跑 N=201 闭合功能测试）。
- limitations 的 `business/problem4 + pipeline/problem4` 双注入 import 链冒烟通过。
