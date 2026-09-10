# A题第一问解决思路与代码解析

## 1. 第一问到底要求什么

第一问研究的是药材在烘干开始后前 30 分钟内的温度和水分浓度变化。

题目给出的药材可以近似看成圆柱：

- 长度：25 cm
- 半径：2 cm
- 初始温度：28 deg C
- 初始水分浓度：2.55 kg/kg

第一问暂时不考虑药材收缩，所以半径始终固定为 2 cm。附件2中半径随时间变化的数据留到第四问使用。

题目要求输出的位置是“到药材中心的距离”：

```text
0, 0.5, 1.0, 1.5, 2.0 cm
```

这里的距离不是长度方向上的距离，而是从圆柱中心轴向外到表面的径向距离。也就是说，第一问求的是药材横截面半径方向上的温度和水分浓度分布：

```text
r = 0 cm      中心轴
r = 2 cm      药材表面
```

由于题目没有要求长度方向上的变化，我们假设药材沿长度方向和圆周方向性质均匀，只考虑半径方向。这就把三维圆柱问题简化成一维径向问题。

## 2. 建模假设

第一问采用以下假设：

1. 药材为均质、各向同性圆柱体。
2. 药材长度方向和圆周方向温度、水分浓度分布均匀，只考虑径向变化。
3. 第一问中药材尺寸不变，半径固定为 2 cm。
4. 药材初始温度和初始水分浓度处处相同。
5. 烘房空气温度和空气水分浓度由附件1给出，中间时刻采用线性插值。
6. 表面通过对流换热和对流传质与烘房空气交换热量和水分。

这些假设的意义是：我们不去计算整个圆柱体的三维场，而是计算从中心到表面的这一条半径线。这样既符合题目输出格式，也能抓住表面先升温、先失水，中心后响应的主要规律。

## 3. 温度模型

药材内部温度满足圆柱坐标下的一维非稳态热传导方程：

```text
partial T / partial t = alpha * (partial^2 T / partial r^2 + 1/r * partial T / partial r)
```

其中：

```text
alpha = k / (rho * cp)
```

第一问给定参数：

```text
rho = 820 kg/m^3
cp  = 2600 J/(kg*K)
k   = 0.36 W/(m*K)
h   = 25 W/(m^2*K)
```

初始条件：

```text
T(r, 0) = 28 deg C
```

中心边界条件：

```text
partial T / partial r = 0, at r = 0
```

这是因为圆柱中心轴是对称位置，热量不会“穿过中心轴”向某一个方向偏流。

表面边界条件：

```text
-k * partial T / partial r = h * (T_surface - T_air)
```

其中 `T_air` 是附件1中烘房温度插值得到的当前时刻空气温度。

## 4. 水分浓度模型

药材内部水分浓度满足圆柱坐标下的一维非稳态扩散方程：

```text
partial C / partial t = 1/r * partial / partial r (r * D * partial C / partial r)
```

第一问给定水分扩散系数：

```text
D = 7e-9 * exp(-0.89C)
```

初始条件：

```text
C(r, 0) = 2.55 kg/kg
```

中心边界条件：

```text
partial C / partial r = 0, at r = 0
```

表面边界条件：

```text
-D * partial C / partial r = hm * (C_surface - C_air)
```

其中：

```text
hm = 8e-7 m/s
```

`C_air` 是附件1中烘房空气水分浓度插值得到的当前时刻值。

直观理解是：药材表面水分先被热风带走，内部水分再慢慢向表面扩散，所以表面水分浓度下降最快，中心下降最慢。

## 5. 数值求解方法

题目要求完整结果为：

```text
时间：每隔 1 s
距离：每隔 0.1 cm
```

所以代码中设置：

```text
dt = 1 s
dr = 0.1 cm = 0.001 m
r = 0, 0.1, 0.2, ..., 2.0 cm
t = 0, 1, 2, ..., 1800 s
```

半径方向共有 21 个网格点，时间方向共有 1801 个时刻。导出 Excel 时按模板从 1 s 到 1800 s 写入，共 1800 行。

我们采用半隐式有限差分法：

- 下一时刻的未知量一起求解，所以稳定性比显式差分更好。
- 每个时间步会形成一个三对角线性方程组。
- 代码用 Thomas 算法求解三对角方程组。
- 水分扩散系数 `D` 依赖当前水分浓度，所以每一步用上一时刻的 `C` 计算 `D`，再推进到下一步。

## 6. 代码文件结构

当前第一问代码分成三个文件。

### 6.1 solver.py

位置：

```text
E:\MathModeling_Coworkbench\code\problem1\solver.py
```

这个文件负责核心模型和数值计算。

主要对象：

```python
EnvironmentSeries
```

保存附件1中的环境数据，包括时间、烘房温度、烘房水分浓度。它有两个方法：

```python
temperature_at(t_s)
moisture_at(t_s)
```

作用是对附件1数据做线性插值。例如附件1每 60 秒给一个数据点，但模型每 1 秒需要一个空气温度和空气水分浓度，所以要插值。

```python
SolverConfig
```

保存第一问的模型参数，例如半径、网格步长、模拟时间、初始温度、初始水分浓度、热学参数和传质系数。

```python
SimulationResult
```

保存模拟结果，包括：

```text
time_s          时间数组
radius_cm       半径位置数组
temperature_c   温度结果矩阵
moisture        水分浓度结果矩阵
```

其中 `temperature_c[i, j]` 表示第 `i` 个时间、第 `j` 个半径位置的温度。

### 6.2 核心函数

```python
build_radial_grid_cm(radius_cm, dr_cm)
```

生成半径网格：

```text
0, 0.1, 0.2, ..., 2.0 cm
```

```python
moisture_diffusivity(c)
```

根据第一问给出的经验公式计算水分扩散系数：

```text
D = 7e-9 * exp(-0.89C)
```

```python
_solve_tridiagonal(lower, diag, upper, rhs)
```

求解三对角线性方程组。半隐式差分每一步都会得到一个三对角方程组，用这个函数快速求解。

```python
_implicit_radial_step(...)
```

推进一个时间步。温度和水分都可以写成“径向扩散 + 表面对流边界”的形式，所以这一个函数被温度模型和水分模型共用。

```python
solve_problem1(environment, config)
```

第一问的总求解函数。它会：

1. 建立半径网格。
2. 建立时间网格。
3. 设置初始温度和初始水分浓度。
4. 每 1 秒推进一次温度。
5. 每 1 秒推进一次水分浓度。
6. 返回完整模拟结果。

### 6.3 run_problem1.py

位置：

```text
E:\MathModeling_Coworkbench\code\problem1\run_problem1.py
```

这个文件负责读取附件1、调用求解器、导出结果。

核心流程是：

```text
读取附件1.xlsx
-> 建立 EnvironmentSeries
-> 调用 solve_problem1
-> 生成温度表和水分浓度表
-> 写入 result1.xlsx
-> 抽取论文表1、表2
-> 写入 problem1_tables.md
```

输出位置：

```text
E:\MathModeling_Coworkbench\results\problem1\result1.xlsx
```

以及：

```text
E:\MathModeling_Coworkbench\results\problem1\problem1_tables.md
```

### 6.4 test_solver.py

位置：

```text
E:\MathModeling_Coworkbench\code\problem1\test_solver.py
```

这个文件负责基础测试，主要检查：

1. 附件1环境数据插值是否正确。
2. 半径网格是否为 `0-2 cm`、间隔 `0.1 cm`。
3. 初始温度和初始水分浓度是否处处一致。
4. 表面温度是否比中心更快升高。
5. 表面水分浓度是否比中心更快下降。
6. 结果中是否没有无穷大或非法数值。

## 7. 如何在 VSCode 中运行

打开文件夹：

```text
E:\MathModeling_Coworkbench
```

在 VSCode 终端中运行：

```powershell
python code\problem1\run_problem1.py
```

如果你的系统默认 Python 缺少 `pandas` 或 `openpyxl`，可以改用 Codex 自带 Python：

```powershell
C:\Users\Lenovo\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe code\problem1\run_problem1.py
```

运行成功后，会生成：

```text
results\problem1\result1.xlsx
results\problem1\problem1_tables.md
```

## 8. 结果怎么看

第一问结果表现出合理的物理趋势：

1. 表面 `r=2 cm` 升温最快，中心 `r=0 cm` 升温最慢。
2. 表面水分浓度下降最快，中心水分浓度几乎不变。
3. 前 30 分钟属于预热和平衡初期，水分主要在靠近表面的区域变化，中心还没有明显失水。

1800 s 时，模拟得到：

```text
中心温度：33.5767 deg C
表面温度：36.7862 deg C
中心水分浓度：2.5500 kg/kg
表面水分浓度：1.4000 kg/kg
```

这个趋势和烘干过程的直觉一致：热风先影响表面，内部响应滞后。

## 9. 论文里可以怎么写

第一问论文表述可以按下面逻辑组织：

1. 将药材视为半径固定的均质圆柱体。
2. 忽略轴向和周向差异，只建立径向一维模型。
3. 对温度建立圆柱坐标下的非稳态热传导方程。
4. 对水分浓度建立圆柱坐标下的非稳态扩散方程。
5. 中心采用对称边界，表面采用对流换热和对流传质边界。
6. 附件1中的烘房温度和水分浓度通过线性插值作为外界条件。
7. 采用半隐式有限差分法求解，并输出题目要求的时间点和空间位置。

一句话总结：

```text
第一问的核心不是直接套附件数据，而是用附件1作为外界条件，建立圆柱径向传热-传质模型，计算药材内部各半径位置随时间变化的温度和水分浓度。
```
