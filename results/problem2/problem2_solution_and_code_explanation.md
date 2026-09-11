# A题第二问解决思路与代码解析

## 1. 问题定位

第二问要求建立整个烘干过程的温度和水分浓度变化模型，并在论文中给出 3 h 内每隔 0.5 h、到药材中心距离为 0、0.5、1、1.5、2 cm 处的温度和水分浓度。

本问仍然不考虑药材半径收缩，计算区域固定为：

```text
r in [0, 2 cm]
```

半径变化数据来自附件2，但只在第四问启用。

## 2. 与第一问的差别

第一问中密度、比热容、热导率是常数；第二问中材料物性由附录3经验公式给出，并随药材内部水分浓度和温度变化。

采用的公式为：

```text
rho(C) = 650 + 128C
cp(C) = 1450 + 2736C/(C+1)
k(C) = 0.21 + 0.38C/(C+1)
D(C,T) = 2.4e-3 * exp(-0.45/C) * exp(-3850/T)
```

其中 `T` 必须使用开尔文温度：

```text
T_K = T_C + 273.15
```

代码中明确使用 `exp(-0.45/C)`，不是 `exp(-0.45*C)`。

## 3. 控制方程

温度方程采用圆柱坐标下一维径向非稳态热传导：

```text
rho(C) cp(C) partial T / partial t
= 1/r * partial / partial r (r k(C) partial T / partial r)
```

水分浓度方程采用守恒形式的径向扩散方程：

```text
partial C / partial t
= 1/r * partial / partial r (r D(C,T) partial C / partial r)
```

中心边界采用对称无通量条件：

```text
partial T / partial r = 0
partial C / partial r = 0
```

表面采用 Robin 边界：

```text
-k partial T / partial r = h (T_surface - T_air)
-D partial C / partial r = hm (C_surface - C_air)
```

由于附录3没有重新给出 `h` 和 `hm`，当前代码沿用附录2参数：

```text
h = 25 W/(m^2*K)
hm = 8e-7 m/s
```

这需要在论文中写成建模假设。

## 4. 数值方法

第二问采用一维径向有限体积风格的空间离散 + 全隐式（backward-Euler）时间推进，并在每个时间步内以 Picard 定点迭代耦合 T/C 两场（空间算子整体隐式求解，并非算子裂解意义上的"半隐式"；agent_A 复核措辞修正 2026-09-10T12:13:40Z）。空间网格和时间网格为：

```text
dr = 0.1 cm
dt = 1 s
t = 0, 1, ..., 10800 s
r = 0, 0.1, ..., 2.0 cm
```

每个时间步内执行 Picard 耦合迭代：

```text
1. 用当前猜测的 C 和 T 计算 rho、cp、k、D
2. 解温度方程得到新的 T
3. 解水分方程得到新的 C
4. 比较新旧 T、C 的最大变化
5. 若小于容差，则该时间步收敛；否则继续迭代
```

这样做是为了回应第二问中 `T` 和 `C` 的双向耦合：

```text
C 影响 rho、cp、k，进而影响温度方程
T 和 C 共同影响 D，进而影响水分扩散
```

默认设置：

```text
max_coupling_iterations = 8
coupling_tolerance = 1e-8
```

完整 10800 个时间步的复核结果为：

```text
全部 10800 步收敛
最大迭代次数为 3
```

## 5. result2.xlsx 是否包含 t=0

题面说完整结果为每隔 1 s、距离每隔 0.1 cm。附件3中的 `result2.xlsx` 模板首列示例从：

```text
1, 2, 3, ...
```

开始，而不是从 `0` 开始。

因此当前导出的 `result2.xlsx` 按模板保存：

```text
t = 1, 2, ..., 10800 s
```

初始条件 `t=0` 不写入 Excel 主表，而是在模型说明中明确：

```text
T(r,0)=28 deg C
C(r,0)=2.55 kg/kg
```

## 6. 代码结构

`code/problem2/solver.py` 负责模型计算。

主要内容：

- `EnvironmentSeries`：保存附件1的烘房温度和水分浓度，并做线性插值。
- `SolverConfig`：保存半径、步长、初始条件、边界系数、Picard迭代上限和收敛容差。
- `density`、`heat_capacity`、`thermal_conductivity`、`moisture_diffusivity`：实现附录3经验公式。
- `_implicit_radial_variable_step`：求解一个变系数径向扩散/传导时间步。
- `solve_problem2`：执行 0 到 10800 s 的完整耦合仿真。

`code/problem2/run_problem2.py` 负责读取附件、运行求解器、导出结果表。

路径不再写死为某台机器的个人目录。运行时有两种方式指定附件1：

```powershell
python code\problem2\run_problem2.py --attachment1 "D:\...\附件1.xlsx"
```

或设置环境变量：

```powershell
$env:CUMCM_A_PROBLEM_DIR = "D:\...\CUMCM2026Problems\A题"
python code\problem2\run_problem2.py
```

如果仓库内存在：

```text
files/raw/CUMCM2026Problems/A题/附件/附件1.xlsx
```

脚本也会自动使用这个相对路径。

`code/problem2/test_solver.py` 负责检查：

- 附录3公式，尤其是 `exp(-0.45/C)` 和 `T+273.15`
- 半径网格是否符合 `0-2 cm`、间隔 `0.1 cm`
- 表面温度升高快于中心，表面水分下降快于中心
- Picard 迭代记录存在且收敛
- 导出切片按附件3模板从 `t=1 s` 开始
- 本解释文档记录关键复核结论

## 7. 输出文件

第二问输出位于：

```text
results/problem2/result2.xlsx
results/problem2/problem2_tables.md
results/problem2/problem2_solution_and_code_explanation.md
```

`result2.xlsx` 包含两个工作表：

- `温度`
- `水分浓度`

每个工作表为：

```text
10800 行 x 22 列
```

其中 1 列为时间，21 列为 `0.0-2.0 cm` 的径向位置。

## 8. 当前方法的边界

当前模型没有加入显式蒸发潜热源项，因为题目没有给出潜热项所需参数。论文中应表述为：在题设经验物性和边界条件下，建立热传导-水分扩散耦合模型，暂不额外引入题目未给定的相变源项。

另外，第二问只输出 0 到 3 h 的结果。附件1覆盖 0 到 4 h，因此该时间段的烘房温湿边界可直接由附件1线性插值得到。超过 4 h 的恒温干燥边界主要影响第三问，需要在第三问中单独确定。

## 9. 网格/时间步无关性与国奖级补强要求

当前主结果采用 `dr=0.1 cm, dt=1 s`，与题目要求的输出网格完全一致；代码测试已验证网格、附录3公式、Picard 耦合收敛和 `t=1 s` 模板切片。这个口径可以保证结果表与附件模板一致，但作为高水平论文仍需补一组网格/时间步无关性说明，避免评委把 `0.1 cm` 误认为“只按输出点粗算”。

建议在论文或附录中补如下复核表，比较 `dr=0.1 cm` 与更细空间网格、`dt=1 s` 与相邻时间步下的表3/表4关键采样值变化：

| 复核项 | 推荐设置 | 判据 |
| --- | --- | --- |
| 空间网格 | `dr=0.1 cm`、`dr=0.05 cm` | 表3/表4采样点最大差异不影响四位小数，或差异量级明确小于建模误差 |
| 时间步长 | `dt=0.5 s`、`dt=1 s`、`dt=2 s` | 表3/表4采样点最大差异不影响四位小数，且 Picard 步均收敛 |
| 耦合收敛 | `max_coupling_iterations=8, tol=1e-8` | 全部 10800 步收敛，最大迭代次数保持较小 |

若时间不足，正文至少应写明：“本问计算网格与题目输出网格一致，已通过耦合收敛与物理趋势测试；更细网格复核作为附录补充。”这样比直接给出表格更诚实，也能避免把未经复核的精度包装成确定结论。
