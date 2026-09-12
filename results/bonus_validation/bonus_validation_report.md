# Bonus validation report

本报告为独立加分验证包输出，不修改任何现有 `problem1`-`problem4` 求解器。

## 1. MMS radial FVM check

制造解取 `u(r)=1+r^2+0.25r^4`，解析径向 Laplacian 为 `4+4r^2`。下表误差统计排除最外层边界半控制体，主要检验内部守恒型径向 FVM 通量离散。

| N | L2 error | max error | rate |
|---:|---:|---:|---:|
| 40 | 9.375000e-04 | 9.375000e-04 |  |
| 80 | 2.343750e-04 | 2.343750e-04 | 2.000 |
| 160 | 5.859375e-05 | 5.859377e-05 | 2.000 |
| 320 | 1.464844e-05 | 1.464854e-05 | 2.000 |

结论：内部空间算子达到接近二阶收敛，可作为论文“离散格式正确性”的轻量证据。

## 2. Bessel analytic mode cross-check

取圆柱 Dirichlet 本征模态 `u(r)=J0(lambda_1 r)`，其中 `lambda_1=2.4048255577` 为 `J0` 第一零点；解析关系为 `Delta_r u = -lambda_1^2 u`。

| N | L2 error | max error | rate |
|---:|---:|---:|---:|
| 40 | 1.089097e-03 | 1.955733e-03 |  |
| 80 | 2.690698e-04 | 4.896736e-04 | 2.017 |
| 160 | 6.686253e-05 | 1.224647e-04 | 2.009 |
| 320 | 1.666475e-05 | 3.061911e-05 | 2.004 |

结论：Bessel 模态从解析结构上覆盖了圆柱坐标奇点附近的正则性处理，可补强“径向模型没有把 1/r 项离散错”的论证。

## 3. Boundary-layer LHS surrogate check

基于已验收的 3x3 边界敏感性结果构建双线性代理面，变量范围为 `Delta T in [-2,2] deg C`、`moisture factor in [0.9,1.1]`，采用 5000 点 Latin Hypercube 采样。该项不是替代全模型重算，而是论文中的快速鲁棒性量化。

| Problem | mean h | std h | p05 h | p50 h | p95 h | temp contribution | moisture contribution |
|---|---:|---:|---:|---:|---:|---:|---:|
| Q3 | 57.3462 | 2.0979 | 54.0903 | 57.3566 | 60.6102 | 0.999 | 0.001 |
| Q4 | 50.9790 | 1.8409 | 48.1038 | 50.9777 | 53.8402 | 0.999 | 0.001 |

结论：在当前边界扰动范围内，终止时间不确定性主要由环境温度扰动贡献，湿度因子贡献较小；这与 Q3/Q4 已有 3x3 敏感性表的方向一致。

## 4. Layered UQ statement for Q4

上述 LHS 代理面只覆盖边界条件层，不应写成 Q4 的总不确定性。A 的 dry-mass closure 诊断指出，题设给定 `R(t)` 与经验密度关系之间的闭合口径会形成更大的模型形式层。因此 Q4 的 UQ 应分层表述：

| Layer | Quantity | Value |
|---|---|---:|
| Boundary-condition layer | LHS p05-p95 | 48.1038 - 53.8402 h |
| Boundary-condition layer | half-width | 2.8682 h |
| Shrinkage/density-closure layer | main answer lower bound | 50.8245 h |
| Shrinkage/density-closure layer | dry-mass-closure upper bound | 60.7312 h |
| Shrinkage/density-closure layer | upper shift | +9.9067 h |
| Ratio | closure shift / boundary half-width | 3.45 |

推荐论文表述：For Q4, the LHS boundary surrogate gives a boundary-condition layer of about +/-2.87 h, whereas the shrinkage/density-closure model-form layer shifts the upper bound by +9.91 h; thus the dominant uncertainty comes from the consistency between the prescribed radius trajectory and the empirical density relation, not from the +/-2 deg C and +/-10% boundary perturbations.

注意：`60.7312 h` 目前来自 `discussion/limitations_fix_analysis_by_A.md` 的诊断值，适合作为分层 UQ 的模型形式上界说明；若要把它作为正式表格 rung，应另建 `problem4_mass_closure/` 做 N=3201 可复现计算。
