# 问题四全局敏感性与刚性求解器交叉验证

本目录在题设直接问题四主模型上实施：

1. 9参数Morris筛选；
2. 对筛选后的5个参数建立Legendre PCE（160个LHS点并加入32个角点）；
3. 用独立高保真PDE样本验证代理；
4. 从PCE正交系数计算Sobol一阶与总效应指数，并以Saltelli代理抽样复核；
5. 用N3201抽查默认、代理快速/慢速样本和最大验证误差点；
6. 用Radau IIA复核默认、快速样本和慢速样本的事件时间与代表时刻全水分剖面。

参数范围是独立均匀的工程扰动假设，不是观测数据识别的概率分布。Sobol结果是筛选后5参数的条件分析，其余4参数固定于基准值。干物质质量闭合替代模型属于离散模型形式层，不放入连续Sobol空间。

运行示例：

```powershell
py code\global_sensitivity\run_pipeline.py `
  --attachment1 "D:\Desktop\CUMCM2026Problems(1)\A题\附件\附件1.xlsx" `
  --attachment2 "D:\Desktop\CUMCM2026Problems(1)\A题\附件\附件2.xlsx" `
  --work-dir "..\work\global_sensitivity" `
  --results-dir "results\global_sensitivity" `
  --workers 4
```

中间样本缓存只写入仓库外的 `work/global_sensitivity/`；仓库中保存参数范围、Morris、PCE、Sobol、高保真抽查、Radau和汇总报告。
