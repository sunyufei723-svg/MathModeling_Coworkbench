# 第 4 层 · 执行层详解（code/ results/ files/）

> 展开 `rules.md`「第 4 层 执行层」：三个产物目录的用途、files 三级子目录、读写规则、入库边界。
> 简洁规则见 [`rules.md`](../rules.md)。

---

## 4.1 作用

执行层存放**实际工作产物**，是数模竞赛交付的主体：

- `code/`：代码（建模、求解、绘图、数据处理脚本）。
- `results/`：实验结果、图表、输出。
- `files/`：文件资料，分三级子目录。

## 4.2 files/ 三级子目录

- `files/raw/`：原始数据（**只读为主**，谁都不该改别人的原始输入）。
- `files/intermediate/`：中间产物。
- `files/final/`：最终交付。

## 4.3 读写规则

- **读**：免锁，只查对应 `locks/<资源>.lock` 里目标路径有无活跃 `W` 锁（有则暂缓读）。
- **写**：拿对应资源的写锁 `W`（`code/`→`code.lock`，`results/`→`results.lock`，`files/`→`files.lock`）。
- **优先锁具体文件 / 目录**，必要时才锁整个资源；多资源按 `code → discussion → files → results` 顺序申请（详见 `docs/5-concurrency.md` 5.9）。

## 4.4 入库边界（.gitignore）

- **入库**：源码、文档、结果图表（png/jpg/pdf）、最终交付。
- **不入库**：大数据集（`*.zip/rar/7z/mat/h5/hdf5/nc`）、Python 缓存（`__pycache__/` 等）、编译产物、Office/LaTeX 临时文件、本机 `identity.md`。
- `files/raw/` 下大数据集默认不入库，避免仓库膨胀；小样本可放行，大数据另传网盘并在 `decisions.md` 记录。
- 结果图与最终交付即使匹配了压缩包忽略规则也**明确放行**（`!results/**/*.png`、`!files/final/**` 等）。
