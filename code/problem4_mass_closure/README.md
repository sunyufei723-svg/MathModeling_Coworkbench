# 问题四 L5「干物质闭合」分支 —— 正式、独立、可复现的替代情景模块

> ⚠️ **本分支不是答案，也非更高精度解。** 题设直接模型主答案仍为
> **t\* = 50.8245 h（N=3201）**，来自 `code/problem4_fvm_bdf`。本模块只回答一个
> 反事实问题：「若**强制干物质守恒**、让半径轨迹由密度演化自洽决定，烘干时长会推迟到多少？」
> 其闭合轨迹与附件 2 题给 R(t) 矛盾（自 t≈19.5 h 起需负含水率才能闭合），故仅作**模型形式对照 / 反事实上界**。

## 缘起（provenance）

第 2 天诊断（`discussion/limitations_fix_analysis_by_A.md` §1.4、gitignored 脚本
`drymass_closure.py`）发现：题设把附件 2 的 R(t) 当已知输入，同时用附录 4 经验密度
ρ(C)=760+90C，这两条题给关系**数学上不自洽**——干物质闭合指标 κ(t)=m(t)/m0 全程有
**28.02%** 相对变幅（κ_min=0.7198 @ t≈7 h）。agent_C 在 `discussion/ideas.md` §五与
`requests/agent_C.md` 正式指派：把该诊断**推进为正式、独立、可复现的 L5 替代情景**，
至少含闭合方程与假设、N401 复现、N3201 生产、空间/时间敏感性、质量闭合核验、与题设
直接模型的同口径比较、单元测试与结果文档。本模块即该交付物。

## 闭合方程与假设

**假设**：圆柱横截面均匀仿射收缩（ξ=r/R(t) 标记固定物质点）、干骨架质量守恒、单位长度体积 ∝ R²。

附录 4 干基固体密度（去水基）：

    ρ_s(C) = ρ(C)/(1+C) = 90 + 670/(1+C)   [kg/m^3],  ρ_s0 = ρ_s(C0=2.55) = 278.7324

定义干物质指数 m(t)=R(t)²·Σ_i ρ_s(C_i)·V̂_i、κ(t)=m(t)/m0、几何因子 G=(R/R0)²、
压缩因子 S=<ρ_s>/ρ_s0，则恒等式 **κ = G·S**。干物质闭合要求 κ≡1，即

    R(t) = R0 / sqrt(S(t))

这构成**不动点迭代**：给定 R_k(t) → 解热湿耦合 PDE（物质坐标 FVM-BDF）→ C(ξ,t)、S_k(t)
→ R_{k+1}(t)=R0/√(S_k(t))（等价 R_{k+1}=R_k/√κ_k）。收敛判据：相邻迭代 |Δt\*|<1e-4 h
**且** κ 相对变幅<1e-4 ⇒ κ≡1（干物质由构造精确守恒）。

## 文件

| 文件 | 作用 |
| --- | --- |
| `closure.py` | 核心：契约自检 + `ClosureConfig/ClosureState/ClosureResult` + `run_closure` 不动点迭代 |
| `run_and_verify.py` | 编排：N401 复现硬校验 → 空间网格扫描 → N3201 生产 → 时间积分敏感 → κ 核验 → 同口径比较 → 写 4 份结果文档；支持 `--resume`（断点续算）与 `--quick`（冒烟） |
| `test_closure.py` | 6 项单元测试（契约/ρ_s0 解析/口径映射/更新式恒等/非有限拒绝/功能） |
| `README.md` | 本文件 |

## 运行

```powershell
# 单元测试（解析/契约测试毫秒级；功能测试需附件，缺失自动跳过）
python code/problem4_mass_closure/test_closure.py

# 开发冒烟（仅 N=401 复现，触发给定模型硬校验，不写完整报告）
python code/problem4_mass_closure/run_and_verify.py --quick

# 全量生产（空间扫描 + N3201 + 时间敏感 + κ 核验 + 写文档，约 15 min）
python code/problem4_mass_closure/run_and_verify.py
# 中断后续算：加 --resume（复用 _work/ 里的 checkpoint）
```

**依赖**：numpy / scipy / pandas / openpyxl；附件 `附件/附件1.xlsx`、`附件/附件2.xlsx`
（gitignored，缺失则功能测试跳过、编排报错）；只读 import `code/problem4_fvm_bdf` 的稳定
已提交 API（`SolverConfig` / `solve_problem4_bdf` / `load_inputs` / `RadiusSeries` /
`build_reference_geometry` / `density`），**不修改其任何文件**。导入时做契约自检：若
agent_C 参数化改动导致 API 漂移，本模块立即显式 `RuntimeError` 而非静默算错。

## 产出（`results/problem4_mass_closure/`）

- `verification.json` —— 全部结构化结果（含附件 sha256、版本、逐节点迭代序列）
- `mass_closure_tables.md` —— 表 L5-1：给定 vs 闭合逐节点对照 + 生产值 + 同口径结论
- `numerical_verification.md` —— 空间网格 Δt\* 收敛 + 时间积分敏感 + κ→1 质量闭合核验 + 复现校验
- `problem4_mass_closure_explanation.md` —— 定位/闭合方程与假设/结果/适用边界/文件

## 关键结果与铁律

- **复现校验**：给定模型 N401 t\*=50.844229 h、N3201 t\*=50.824507 h（逐位复现主求解器基线，
  证明只读 import 与配置同源）；闭合模型 N401 t\*≈60.73 h（复现诊断归档值）。
- **生产口径 N3201**：闭合把 t\* 从 50.8245 h 推迟约 +19%（详见 `mass_closure_tables.md`）。
- **质量闭合**：给定 κ 变幅 28.02% → 闭合 κ→1（干物质守恒由构造保证）。
- **铁律**：**绝不用未经验证的 60.7312 h 替换题设直接模型主答案 50.8245 h**；闭合分支
  不进入论文表 6/表 7 的答案列，只作模型形式敏感性对照。
