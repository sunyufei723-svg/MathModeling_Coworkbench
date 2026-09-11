# problem4_improved_fvmbdf

问题4独立改进副本。此文件夹不改动 `E:\MathModeling_Coworkbench` 源文件。

核心改动：

- 继续使用 FVM-BDF1：守恒有限体积 + 一阶后向差分 + Picard 耦合。
- `SolverConfig` 默认空间网格改为 201 点，和生产命令一致。
- 水分扩散界面系数改为谐波平均，以适配后期强干燥下 `D(C,T)` 跨数量级变化。
- 输出路径固定到仓库的 `results/problem4_improved_fvmbdf/`。

验证：

```powershell
cd E:\MathModeling_Coworkbench\code\problem4_improved_fvmbdf
py -m unittest -v
```

生成结果：

```powershell
py run_problem4.py --attachment1 "附件1.xlsx的路径" --attachment2 "附件2.xlsx的路径" --xi-points 201 --dt 10
```
