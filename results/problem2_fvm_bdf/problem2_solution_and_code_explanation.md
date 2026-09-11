# 问题二改进解：严格径向 FVM + 联合状态自适应 BDF

## 1. 独立版本说明

本目录与 `code/problem2_fvm_bdf/` 是问题二的改进解。原有 `code/problem2/`、`results/problem2/` 完整保留，用于数值方法对照，不再作为本改进方案的最终答案。

本次检查远程仓库后确认：原问题二近期只增加了 Excel 四位小数显示和验证说明，核心求解器仍是 `dr=0.1 cm`、固定 `1 s` 后向欧拉、Picard 迭代与界面算术平均，尚未实现这里要求的严格 FVM+BDF 重构。

## 2. 双向耦合模型

把全部温度节点和全部水分节点合并为一个状态向量：

\[
\mathbf y=(T_0,\ldots,T_N,C_0,\ldots,C_N)^\mathsf T.
\]

在半径为 `R=2 cm` 的圆柱径向截面上求解：

\[
\rho(C)c_p(C)\frac{\partial T}{\partial t}
=\frac1r\frac{\partial}{\partial r}\left(rk(C)\frac{\partial T}{\partial r}\right),
\]

\[
\frac{\partial C}{\partial t}
=\frac1r\frac{\partial}{\partial r}\left(rD(C,T)\frac{\partial C}{\partial r}\right).
\]

附录 3 的变物性写为：

\[
\rho=650+128C,\quad
c_p=1450+\frac{2736C}{C+1},\quad
k=0.21+\frac{0.38C}{C+1},
\]

\[
D=2.4\times10^{-3}\exp\!\left(-\frac{0.45}{C}\right)
\exp\!\left(-\frac{3850}{T+273.15}\right).
\]

因此水分通过 `ρ、cp、k` 影响温度方程，温度又通过 `D(C,T)` 影响水分方程，构成真正的双向非线性耦合。初值仍从 `t=0` 的 `T=28 °C、C=2.55 kg/kg` 开始，不能承接问题一末态；附件 1 的环境温度和水分按时间线性插值。表面对流系数沿用附录 2：`h=25 W/(m²·K)`、`hm=8e-7 m/s`。

中心采用对称条件，表面采用 Robin 边界：

\[
k\frac{\partial T}{\partial r}=h(T_\infty-T_s),\qquad
D\frac{\partial C}{\partial r}=h_m(C_\infty-C_s).
\]

与原解一致，题目未给出可闭合的相变潜热参数，因此温度方程不额外加入显式蒸发潜热项；这一点是模型假设，不是数值算法遗漏。

## 3. 严格径向有限体积离散

采用包含中心和表面节点的节点型控制体。对单位轴向长度，节点 `i` 的控制体体积和界面面积为：

\[
V_i=\pi(r_{i+1/2}^2-r_{i-1/2}^2),\qquad
A_{i+1/2}=2\pi r_{i+1/2}.
\]

中心控制体左边界面积自然为 0，表面节点使用半控制体，外部 Robin 通量直接进入表面控制体，因而无需人为写 `1/r` 的中心奇点差分。

界面传输系数统一采用调和平均：

\[
k_{i+1/2}=\frac{2k_ik_{i+1}}{k_i+k_{i+1}},\qquad
D_{i+1/2}=\frac{2D_iD_{i+1}}{D_i+D_{i+1}}.
\]

这比原方案的算术平均更符合串联扩散阻力的通量计算，尤其适合表面干燥前沿附近变化明显的扩散系数。

## 4. BDF 时间积分与稀疏结构

空间离散后得到 162 维主系统（81 个温度节点 + 81 个水分节点），一次性交给 SciPy 的自适应 BDF 积分器。主计算参数为：

- 内部网格 `dr=0.025 cm`；
- `rtol=2e-8`；
- 温度和水分的分量绝对容差分别为 `2e-9`、`2e-10`；
- `max_step=5 s`；
- 导出时间与内部步长分离，每隔 `1 s` 输出一次。

Jacobian 稀疏模式由四个三对角块组成：温度-温度、温度-水分、水分-温度、水分-水分都只连接本节点及相邻节点。该结构使求解器能使用稀疏差分 Jacobian 和稀疏线性代数，而不必构造稠密的 `162×162` 或 `322×322` 矩阵。

内部细网格的 0、0.1、…、2.0 cm 均与节点重合，导出时用精确索引抽取；求解器也保留了非整倍网格时的线性插值后备路径。`result2.xlsx` 不写入内部 `t=0` 初值行，按原模板从 `t=1 s` 输出到 `10800 s`，共 10800 行数据和 21 个半径列。

## 5. 代码与产物

- `code/problem2_fvm_bdf/solver.py`：物性、严格径向 FVM、联合状态 RHS、稀疏 Jacobian 结构、自适应 BDF 与细网格抽取。
- `code/problem2_fvm_bdf/run_and_verify.py`：主计算、空间加密、BDF 时间敏感性、初期超细网格诊断、新旧结果比较，并生成 Excel 导出数据。
- `code/problem2_fvm_bdf/test_solver.py`：网格、几何守恒、调和平均、稀疏结构、常量场及短时联合求解测试。
- `code/problem2_fvm_bdf/export_result2.mjs`：在原模板结构上写入温度/水分数据，统一显示四位小数并校验工作簿。
- `results/problem2_fvm_bdf/result2.xlsx`：本改进方案的完整 1 s 输出。
- `results/problem2_fvm_bdf/problem2_tables.md`：可直接用于论文的表 3、表 4。
- `results/problem2_fvm_bdf/numerical_verification.md`：空间、时间、初期边界层及新旧方案的量化对照。

## 6. 数值验证结论

在论文表 3、表 4 的 30 个采样点上，`dr=0.025 cm` 与 `0.0125 cm` 的最大差为：

\[
\max|\Delta T|=4.15597\times10^{-5}\ ^\circ\mathrm C,
\qquad
\max|\Delta C|=4.66835\times10^{-5}\ \mathrm{kg/kg}.
\]

把 BDF 从主参数收紧到 `rtol=1e-9`、温度/水分 `atol=1e-10/1e-11`、`max_step=2 s` 后，论文采样点的最大变化仅为：

\[
\max|\Delta T|=1.91308\times10^{-5}\ ^\circ\mathrm C,
\qquad
\max|\Delta C|=4.84443\times10^{-8}\ \mathrm{kg/kg}.
\]

所以论文表格对空间加密和 BDF 参数均已稳定。此前声称的水分网格误差 `4.67e-5` 可复现；温度的同量级结论可复现，但重新计算值为 `4.16e-5`，不应继续写成未经本代码复现的 `3.97e-5`。

完整 1 s 输出还揭示了一个局限：最初几秒的表面水分边界层非常薄，`dr=0.025 cm` 与 `0.0125 cm` 在 `t=2 s` 的表面最大相差 `0.0108660 kg/kg`；`0.0125 cm` 与 `0.00625 cm` 在 `t=1 s` 仍相差 `0.00497361 kg/kg`。这不影响 0.5–3 h 的论文表格结论，但若研究对象改为最初几秒的表面瞬态，应继续局部加密。

## 7. 最终答案

表 3、表 4 的完整数值见 `problem2_tables.md`。3 h 时关键结果为：

\[
T(0)=49.8495\ ^\circ\mathrm C,\quad T(2\,\mathrm{cm})=49.9664\ ^\circ\mathrm C,
\]

\[
C(0)=1.7662\ \mathrm{kg/kg},\quad C(2\,\mathrm{cm})=1.0081\ \mathrm{kg/kg}.
\]

相对原方案，新解整体表现为温度略低、水分略高，即预测升温和干燥都略慢；3 h 时中心/表面温度分别低约 `0.0036/0.0028 °C`，中心/表面水分分别高约 `0.0037/0.0088 kg/kg`。两者的物理判断一致：3 h 时温度几乎平衡，但水分仍有明显空间梯度。
