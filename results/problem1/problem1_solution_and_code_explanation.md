# A题第一问解决思路与代码解析（修正版）

## 1. 修正结论

本版覆盖旧版问题一求解。核心修正有四项：

1. 水分扩散系数改为题设公式
   \[
   D(C)=7\times10^{-9}\exp\!\left(-\frac{0.89}{C}\right)\ \mathrm{m^2/s},
   \]
   不再使用错误的 \(7\times10^{-9}\exp(-0.89C)\)。
2. 水分方程保持 Fick 定律的守恒形式，不能把变系数 \(D(C)\) 直接移到散度算子之外。
3. 数值方法统一为一维径向有限体积法（FVM）与隐式 BDF 时间积分。
4. 区分计算网格和输出网格：内部使用 \(\Delta r=0.0025\rm\,cm\)，最终仍按题目要求每 1 s、每 0.1 cm 输出。

## 2. 几何简化与模型选择

药材视为半径 \(R=2\rm\,cm\)、长度 \(L=25\rm\,cm\) 的圆柱。初始温度和干基含水率分别为

\[
T_0=28^\circ\mathrm C,\qquad C_0=2.55\ \mathrm{kg/kg}.
\]

热扩散率为

\[
\alpha=\frac{k}{\rho c_p}
=\frac{0.36}{820\times2600}
\approx1.6886\times10^{-7}\ \mathrm{m^2/s}.
\]

热、质传递 Biot 数分别约为

\[
Bi_T=\frac{hR}{k}\approx1.389,
\qquad
Bi_C=\frac{h_mR}{D(2.55)}\approx3.24.
\]

二者均明显大于 0.1，不能把药材内部温度或含水率视为空间均匀。另一方面，1800 s 内热、水分扩散尺度约为

\[
\sqrt{\alpha t}\approx1.74\rm\,cm,
\qquad
\sqrt{D(2.55)t}\approx0.30\rm\,cm,
\]

都远小于圆柱半长 12.5 cm。因此忽略端面和轴向变化，取

\[
T=T(r,t),\qquad C=C(r,t),\qquad 0\le r\le R.
\]

## 3. 控制方程与边界条件

第一问的 \(\rho,c_p,k\) 为常数，且 \(D\) 只依赖 \(C\)，所以温度场和水分场可以独立求解。

温度场采用守恒型 Fourier 方程：

\[
\rho c_p\frac{\partial T}{\partial t}
=\frac1r\frac{\partial}{\partial r}
\left(kr\frac{\partial T}{\partial r}\right).
\]

水分场采用守恒型非线性 Fick 方程：

\[
\frac{\partial C}{\partial t}
=\frac1r\frac{\partial}{\partial r}
\left[rD(C)\frac{\partial C}{\partial r}\right],
\qquad
D(C)=7\times10^{-9}\exp\!\left(-\frac{0.89}{C}\right).
\]

中心为对称边界：

\[
T_r(0,t)=0,\qquad C_r(0,t)=0.
\]

表面为 Robin 边界：

\[
-kT_r(R,t)=h\,[T_s-T_\infty(t)],
\]

\[
-D(C_s)C_r(R,t)=h_m\,[C_s-C_\infty(t)].
\]

附件 1 的 \(T_\infty(t)\) 和 \(C_\infty(t)\) 在相邻实测时刻之间使用分段线性插值。

本问没有声称实际烘干不存在蒸发潜热。这里仅按照题设给出的参数体系，采用热传导与水分扩散解耦的最小闭合模型，不额外引入题目未给定的潜热及热湿耦合源项。

## 4. 有限体积离散与 BDF 积分

令节点 \(r_i=i\Delta r\)，节点控制体体积和控制面面积分别为

\[
V_i=\pi\left(r_{i+1/2}^2-r_{i-1/2}^2\right),
\qquad
A_{i+1/2}=2\pi r_{i+1/2}.
\]

长度方向取单位长度。温度内部节点离散为

\[
\rho c_pV_i\frac{dT_i}{dt}
=kA_{i-1/2}\frac{T_{i-1}-T_i}{\Delta r}
+kA_{i+1/2}\frac{T_{i+1}-T_i}{\Delta r}.
\]

水分界面扩散系数采用算术平均

\[
D_{i+1/2}=\frac{D(C_i)+D(C_{i+1})}{2},
\]

于是

\[
V_i\frac{dC_i}{dt}
=D_{i-1/2}A_{i-1/2}\frac{C_{i-1}-C_i}{\Delta r}
+D_{i+1/2}A_{i+1/2}\frac{C_{i+1}-C_i}{\Delta r}.
\]

表面控制体直接加入对流换热或对流传质通量，中心控制体天然满足零通量条件，不需要人为设置 ghost point。空间离散后得到两组常微分方程，用稀疏三对角 Jacobian 结构的 BDF 方法积分至 1800 s。

内部计算网格为 801 个节点（\(\Delta r=0.0025\rm\,cm\)）；输出时抽取

\[
r=0,0.1,\ldots,2.0\rm\,cm,
\qquad
t=1,2,\ldots,1800\rm\,s.
\]

网格加密复核中，内部网格从 0.005 cm 加密至 0.0025 cm 后，论文所列抽样单元的最大变化约为 \(1.1\times10^{-4}\ ^\circ\mathrm C\) 和 \(5.6\times10^{-5}\ \mathrm{kg/kg}\)，说明当前结果已达到题目四位小数输出所需的稳定量级。

## 5. 代码结构与复现流程

- `solver.py`：参数、时变边界插值、守恒型径向 FVM 和 BDF 求解。
- `run_problem1.py`：读取边界 JSON/CSV，求解，生成工作簿数据载荷与论文表格。
- `extract_environment.mjs`：从附件 1 工作簿提取“时间、温度、水分浓度”三列。
- `export_result1.mjs`：保留模板双工作表结构，写入完整结果并统一四位小数格式。
- `test_solver.py`：检查扩散系数公式、网格分离、边界插值和基本物理趋势。

在仓库根目录运行：

```powershell
node code/problem1/extract_environment.mjs --input "附件1.xlsx" --output "work/problem1_environment.json"
python code/problem1/run_problem1.py --environment "work/problem1_environment.json" --payload "work/problem1_result.json"
node code/problem1/export_result1.mjs --template "results/problem1/result1.xlsx" --payload "work/problem1_result.json" --output "results/problem1/result1.xlsx"
python -m unittest discover -s code/problem1 -p "test_*.py" -v
```

Python 依赖见 `requirements.txt`。两个 `.mjs` 脚本使用当前 Codex 工作区提供的 `@oai/artifact-tool` 工作簿运行时。

## 6. 最终结果与物理解释

完整结果见 `result1.xlsx`，论文抽样值见 `problem1_tables.md`。1800 s 时：

\[
T(0,1800)=33.5753^\circ\mathrm C,
\qquad
T(R,1800)=36.7856^\circ\mathrm C,
\]

\[
C(0,1800)=2.5500\ \mathrm{kg/kg},
\qquad
C(R,1800)=1.5102\ \mathrm{kg/kg}.
\]

表面先升温、先失水，中心响应明显滞后。30 min 时热扰动已深入大部分半径，而显著失水仍主要集中在表层，这与热扩散尺度约 1.74 cm、水分扩散尺度约 0.30 cm 的数量级判断一致。
