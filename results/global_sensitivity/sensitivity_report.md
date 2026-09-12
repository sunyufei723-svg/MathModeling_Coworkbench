# 问题四全局敏感性、PCE/Sobol与Radau验证报告

本报告只研究题设直接给定的物质坐标问题四主模型。干物质质量闭合替代模型是离散的模型形式层，不混入连续Sobol参数空间。所有参数均按声明的独立均匀工程扰动分布处理，因此结论不是由观测数据估计的统计置信区间。

## 1. Morris筛选

采用 20 条轨迹、200 次N401高保真PDE计算。mu_star衡量筛选影响强度，不能解释成方差贡献率。

| 排名 | 参数 | mu/h | mu_star/h | sigma/h |
|---|---|---|---|---|
| 1 | activation_temperature_factor | 61.657372 | 61.657372 | 10.354733 |
| 2 | diffusivity_prefactor_factor | -10.116694 | 10.116694 | 3.932812 |
| 3 | ambient_temperature_delta_c | -6.185178 | 6.185178 | 2.360775 |
| 4 | shrinkage_amplitude_factor | -5.623474 | 5.623474 | 1.979695 |
| 5 | mass_transfer_factor | -0.490940 | 0.490940 | 0.106609 |
| 6 | ambient_moisture_factor | 0.169482 | 0.169482 | 0.050304 |
| 7 | heat_transfer_factor | -0.015424 | 0.015424 | 0.001994 |
| 8 | density_intercept_factor | 0.007046 | 0.007046 | 0.001056 |
| 9 | density_slope_factor | 0.003776 | 0.003776 | 0.000498 |

进入PCE/Sobol的参数：activation_temperature_factor, diffusivity_prefactor_factor, ambient_temperature_delta_c, shrinkage_amplitude_factor, mass_transfer_factor

## 2. PCE代理及独立验证

最终采用 4 阶Legendre PCE；训练样本 192 个，独立验证样本 40 个。

独立验证：Q²=0.999999821，RMSE=0.006856 h，最大绝对误差=0.025037 h，NRMSE=0.000114。验收：通过。

在保留的5个变量服从所声明独立均匀分布、其余4个变量固定于基准值的条件下，PCE抽样均值=53.8177 h，标准差=16.6868 h，P5=32.1225 h，中位数=50.9290 h，P95=83.9961 h。该范围是工程扰动假设下的条件分布，不是统计置信区间。

## 3. Sobol方差分解

以下Sobol指数由通过独立PDE验证的正交PCE系数计算，并用廉价Saltelli抽样交叉检查。它是Morris筛选后5参数的条件Sobol分析；未入选的4个参数固定在基准值。尤其应注意，活化温度参数的主导程度依赖于预先声明的±5%工程范围。

| 参数 | 一阶S_i | 总效应S_Ti | 一阶95%区间 | 总效应95%区间 |
|---|---|---|---|---|
| activation_temperature_factor | 0.94036 | 0.94713 | [0.940342, 0.940386] | [0.947109, 0.947154] |
| diffusivity_prefactor_factor | 0.02735 | 0.03074 | [0.027339, 0.027369] | [0.030723, 0.030753] |
| ambient_temperature_delta_c | 0.01409 | 0.01624 | [0.014080, 0.014101] | [0.016231, 0.016251] |
| shrinkage_amplitude_factor | 0.01123 | 0.01271 | [0.011224, 0.011242] | [0.012696, 0.012716] |
| mass_transfer_factor | 0.00008 | 0.00008 | [0.000078, 0.000079] | [0.000081, 0.000082] |

一阶指数和=0.993119；PCE解析值与Saltelli数值值的最大差=0.003397，验收：通过。

最大的二阶交互项为：

| 参数1 | 参数2 | 二阶指数 |
|---|---|---|
| activation_temperature_factor | diffusivity_prefactor_factor | 0.003280 |
| activation_temperature_factor | ambient_temperature_delta_c | 0.002066 |
| activation_temperature_factor | shrinkage_amplitude_factor | 0.001402 |

表中95%区间仅量化PCE拟合残差经重抽样后造成的代理系数不确定性；它们不是参数分布、观测误差或模型形式的统计置信区间。

## 4. N3201高保真抽查

| 情景 | PCE/h | PDE/h | 绝对误差/h |
|---|---|---|---|
| default | 50.825299 | 50.824507 | 0.000792 |
| surrogate_fast_sample | 26.635799 | 26.647868 | 0.012068 |
| surrogate_slow_sample | 108.552244 | 108.521763 | 0.030481 |
| worst_validation_3 | 38.552868 | 38.536774 | 0.016093 |
| worst_validation_4 | 92.474211 | 92.472588 | 0.001623 |
| worst_validation_5 | 74.362983 | 74.327229 | 0.035754 |

默认参数化求解器相对既有基准182968.225162 s的差=0.000000 s；总体验收：通过。

## 5. Radau IIA交叉验证

| 情景 | BDF/h | Radau/h | 差异/s | 代表剖面最大水分差 |
|---|---|---|---|---|
| default | 50.825422 | 50.825422 | 0.0000 | 2.679e-07 |
| surrogate_fast_sample | 26.648009 | 26.648009 | 0.0003 | 1.732e-08 |
| surrogate_slow_sample | 108.527369 | 108.527369 | 0.0004 | 1.601e-07 |

Radau只用于默认、快速样本和慢速样本三个情景，不参与批量UQ。事件时间差小于30 s且代表时刻全剖面最大水分差小于1e-4的联合验收：通过。

## 6. 结论边界

Morris用于筛选而非方差归因；Sobol指数是在给定独立均匀工程扰动范围下、基于经高保真PDE验证的PCE代理得到。结果不替换问题四主答案50.8245 h，也不包含收缩/密度闭合替代模型的离散模型形式不确定性。
