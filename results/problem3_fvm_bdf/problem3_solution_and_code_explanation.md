# A题问题三严格径向 FVM+BDF 解法与代码说明

## 1. 最终结论

在附件1最后一个边界数据点持续延拓的默认口径下，连续临界时间为

\[
\boxed{t^*=205821.7420\ \mathrm s=57.172706\ \mathrm h}.
\]

该时刻是 \(\max_r C(r,t)\) 首次达到 0.15 的连续事件时刻。第一个严格满足全域 \(C<0.15\) 的 60 s 输出时刻为

\[
\boxed{t_{60}=205860\ \mathrm s=57.183333\ \mathrm h}.
\]

前一报告时刻 205800 s 的最大水分为 0.1500063718，205860 s 为 0.1499887914，因此 Excel 截止行没有提前一格或延后一格。

## 2. 物理模型

问题三固定药材半径 \(R=2\ \mathrm{cm}\)，不考虑收缩；收缩边界属于问题四。状态向量合并为

\[
\mathbf y=[T_0,\ldots,T_N,C_0,\ldots,C_N]^\mathsf T.
\]

附录3物性为

\[
\rho(C)=650+128C,
\]

\[
c_p(C)=1450+2736\frac{C}{C+1},
\]

\[
k(C)=0.21+0.38\frac{C}{C+1},
\]

\[
D(C,T)=2.4\times10^{-3}
\exp\!\left(-\frac{0.45}{C}\right)
\exp\!\left(-\frac{3850}{T+273.15}\right).
\]

代码只在计算物性时使用 \(C_{\rm safe}=\max(C,10^{-9})\)，不修改求解状态。耦合路径为

\[
C\rightarrow(\rho,c_p,k)\rightarrow T,
\qquad
(T,C)\rightarrow D\rightarrow C.
\]

热方程和水分方程均写成圆柱径向守恒形式。表面使用

\[
F_R^T=hA_R(T_{\rm env}-T_N),\qquad
F_R^C=h_mA_R(C_{\rm env}-C_N),
\]

其中 \(h=25\ \mathrm{W/(m^2\,K)}\)、\(h_m=8\times10^{-7}\ \mathrm{m/s}\) 沿用附录2，属于建模假设。题目没有提供蒸发潜热闭合参数，因此不额外加入显式潜热项。

## 3. 两阶段环境边界

附件1覆盖 \(0\le t\le14400\ \mathrm s\)。第一阶段按附件三列数据做分段线性插值；第二阶段默认保持附件末点

\[
T_{\rm env}=50.165\ ^\circ\mathrm C,\qquad
C_{\rm env}=0.04986\ \mathrm{kg/kg}.
\]

求解器先积分到 14400 s 并保存完整联合状态，再以该状态继续第二阶段。这样边界形式切换只发生一次，也便于替换 30 min 平均、1 h 平均和工程扰动情景。

## 4. 严格圆柱径向有限体积法

内部节点为 \(r_i=i\Delta r\)。控制体体积和界面面积分别为

\[
V_i=\pi(r_{i+1/2}^2-r_{i-1/2}^2),\qquad
A_{i+1/2}=2\pi r_{i+1/2}.
\]

中心和表面自然形成半控制体；几何单元测试验证 \(\sum_iV_i=\pi R^2\)。同一内部界面通量以相反符号写入左右控制体，内部通量严格相消。

界面热导率和扩散系数使用调和平均：

\[
k_{i+1/2}=\frac{2k_ik_{i+1}}{k_i+k_{i+1}},\qquad
D_{i+1/2}=\frac{2D_iD_{i+1}}{D_i+D_{i+1}}.
\]

代码保留 `interface_mean="harmonic"|"arithmetic"`，用于消融实验。由于后期表层 \(C\) 很低、\(D\) 跨多个数量级，调和平均会暴露很薄的低扩散系数层；粗网格不能解析该层，因此必须进行比原计划更深的空间加密。

## 5. BDF 主求解器

`solver_bdf.py` 使用 `solve_ivp(method="BDF")`，为四个最近邻三对角耦合块提供 Jacobian 稀疏结构。BDF 内部自适应步长与 60 s 输出网格完全分离。

事件函数为

```python
return np.max(state[node_count:]) - 0.15
```

并设置 `terminal=True`、`direction=-1`。事件不预先假设中心是最大值；计算后确认全程径向分布在容差内单调递减，事件最大值位于中心。

原计划的主网格 0.025 cm 未通过网格无关性。二倍加密一直推进到

\[
\boxed{\Delta r=0.00078125\ \mathrm{cm}},
\]

即 2561 个内部节点、5122 维联合状态。相邻的 0.0015625 cm 网格与该网格的事件时间差为 39.3365 s，相对差为 \(1.91\times10^{-4}\)，表5采样点最大差为 \(2.28\times10^{-5}\ \mathrm{kg/kg}\)，全部通过验收。

最终 BDF 使用 `rtol=1e-8`、温度 `atol=1e-8`、水分 `atol=1e-10`、`max_step=30 s`。更严格的 B3 配置与其事件时间只差 0.00015 s。

## 6. 后向欧拉交叉验证

`solver_be.py` 与 BDF 共享完全相同的 FVM 几何、物性、调和平均、初值和边界。每步采用 Backward Euler + Picard，并用编译的三对角消元求解；若 Picard 达到上限仍未收敛，立即抛出错误。

在选定空间网格上，BE 的 20、10、5、2.5 s 时间步依次得到 57.190191、57.181424、57.177083、57.174913 h。最后两级相差 7.8125 s，最细 BE 与严格 BDF 相差 7.9453 s；全部 Picard 步收敛。

## 7. 非负性、守恒和最大值检查

正式运行没有裁剪任何状态：最小原始水分为 0.0525350982，裁剪单元数为 0。归一化离散水分守恒残差最大为 \(1.08\times10^{-16}\)。输出网格所有时刻的最大水分均位于中心；内部超细网格有 4 个极早时刻的 `argmax` 因机器舍入落在相邻节点，但全径向单调性检查均通过，且最大值相对中心的差异处于设定容差内。

## 8. Excel 与论文时间口径

论文表5包含 6、12、…、54 h 和精确事件时间 \(t^*\)。`result3.xlsx` 不插入事件行，只输出

\[
60,120,\ldots,205860\ \mathrm s.
\]

工作簿只有“水分浓度”一张表，共 22 列、3431 行数据；A列为整数，B–V列显示四位小数。事件判断和验证始终使用原始精度。

## 9. 边界不确定性

默认末点延拓给出 57.172706 h。最后 30 min 和最后 1 h 时间平均延拓分别给出 57.458319 h 和 57.482871 h。讨论中的 57.4778 h 与“最后1 h平均”情景仅差 18.26 s，因此该候选值可以复现，但它不是默认末点延拓的答案。

全部边界情景的范围为

\[
\boxed{53.6154\ \mathrm h\le t^*\le61.0702\ \mathrm h}.
\]

边界假设误差远大于空间、时间离散误差，因此论文正文建议报告默认预测 `57.17 h`，同时给出边界敏感性区间。

## 10. 复现方式

```powershell
python -m unittest discover -s code/problem3_fvm_bdf -p "test_*.py" -v

python code/problem3_fvm_bdf/run_and_verify.py `
  --attachment1 "<附件1.xlsx>" `
  --work-dir "<仓库外工作目录>" `
  --payload "<仓库外工作目录>/excel_payload.json" `
  --verification "results/problem3_fvm_bdf/verification.json"
```

Excel 由 `export_result3.mjs` 使用原 `results/problem3/result3.xlsx` 作为模板生成。原 `code/problem3` 和 `results/problem3` 均未修改。
