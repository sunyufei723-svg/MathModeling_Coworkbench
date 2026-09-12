# bonus_validation

本目录存放不修改现有求解器主体的高价值加分验证项。

包含内容：

- `run_bonus_validation.py`：独立运行脚本，生成解析/MMS/UQ 验证报告。
- `test_bonus_validation.py`：保护 Q4 分层 UQ 表述，避免把边界扰动 LHS 误写成总不确定性。
- `check_repo_portability.py`：扫描 `code/`、`results/`、`files/`，防止解法交付物残留本机绝对路径或临时仓库名。
- 输出目录：`results/bonus_validation/`

验证覆盖：

1. 径向有限体积空间算子的 MMS 收敛检验。
2. Bessel 解析模态对径向柱坐标扩散算子的交叉检验。
3. 基于已验收 3x3 边界敏感性表的 Latin Hypercube 代理不确定性分析。
4. Q4 分层 UQ 表述：边界扰动层与收缩/密度闭合模型形式层分开报告。

运行：

```powershell
py code\bonus_validation\run_bonus_validation.py
py -m unittest discover -v -s code\bonus_validation
py code\bonus_validation\check_repo_portability.py
```

该脚本只依赖 `numpy` 和 `scipy`，不读取附件数据，不改动 `problem1` 到 `problem4` 的任何现有代码。
