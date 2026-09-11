# 数模国赛 · 三人 × Agent 共享工作区

一个用 **git 仓库**搭建的协作工作区：3 名队员各用一个 agent（1 个 Qoder + 2 个 codex），在各自电脑上通过远程仓库协同完成数学建模国赛。

核心是一套**写锁协议**，保证多个 agent 并发写共享文件时不互相覆盖（读取一律免锁）。整个项目按 **5 层**组织，另设最终论文质量规则；规则**简洁版给 AI 主读、详细解释与例子放 `docs/` 按需读**。

## 文档给谁看

| 文件 | 面向 | 作用 |
|---|---|---|
| `README.md`（本文件） | **人（队员）** | 总览 + 5 层导航 + 上手 |
| [`AGENTS.md`](AGENTS.md) | **agent 入口** | codex 自动读，极简摘要 + 导向 rules.md |
| [`rules.md`](rules.md) | **agent 规则** | 简洁权威协议，最高优先级 |
| [`docs/1~6-*.md`](docs/) | **agent 详解** | 各层详细解释 + 论文质量规则 + 完整 git 命令 + 例子，看不懂简洁版时读 |

## 项目结构：5 层

| 层 | 目录 / 文件 | 职责 | 详解 |
|---|---|---|---|
| **1 工作规范** | `identity.md` `rules.md` `AGENTS.md` | 你是谁、铁律、git 规范、红线 | [`docs/1-work-norms.md`](docs/1-work-norms.md) |
| **2 通信层** | `requests/` | agent 间异步通信：状态板、@请求、认领回报 | [`docs/2-communication.md`](docs/2-communication.md) |
| **3 知识层** | `discussion/` | 共享知识：题目拆解 / 思路 / 决策（只追加） | [`docs/3-knowledge.md`](docs/3-knowledge.md) |
| **4 执行层** | `code/` `results/` `files/` | 工作产物：代码 / 结果 / 原始·中间·最终文件 | [`docs/4-execution.md`](docs/4-execution.md) |
| **5 并发控制层** | `locks/` | 写锁协议：串行化并发写、防覆盖、防死锁 | [`docs/5-concurrency.md`](docs/5-concurrency.md) |

## 目录树

```
.
├── AGENTS.md          # 【1 工作规范】agent 入口（codex 自动读，极简）
├── rules.md           # 【1 工作规范】agent 简洁权威协议（最高优先级）
├── README.md          # 【1 工作规范】本文件：人看的总览 + 5 层导航
├── identity.md        # 【1 工作规范】本机 agent 身份（不入库）
├── docs/              # 【1 工作规范】各层详解 + 例子（agent 按需读）
│   ├── 1-work-norms.md      2-communication.md     3-knowledge.md
│   ├── 4-execution.md       5-concurrency.md       6-paper-quality.md
├── .gitignore  .gitattributes
│
├── requests/          # 【2 通信层】每人只写自己的，免锁
│   └── agent_A.md  agent_B.md  agent_C.md
├── discussion/        # 【3 知识层】共享知识，只追加、署名+UTC
│   └── problem.md  ideas.md  decisions.md
├── code/              # 【4 执行层】代码
├── results/           # 【4 执行层】实验结果、图表、输出
├── files/             # 【4 执行层】raw/ 原始 · intermediate/ 中间 · final/ 最终
└── locks/             # 【5 并发控制层】写锁文件，只能按协议编辑
    └── code.lock  results.lock  discussion.lock  files.lock
```

## 快速上手

```bash
# 1) 克隆仓库（远程地址由队长提供）
git clone <远程仓库地址> modeling
cd modeling

# 2) 认领身份：在本机建 identity.md 写上你是 agent_A / agent_B / agent_C（不入库）
#    并在 requests/agent_<你>.md 顶部写负责方向

# 3) 每次开工先同步
git pull --rebase
```

## 核心流程一句话

- **读**共享文件：`pull` → 查目标有无活跃写锁 W → 直接读（**免锁、0 push**）。
- **写**共享文件：`pull` →〔状态 + 锁〕一次 push → 本地写 →〔内容 + 解锁 + 状态〕一次 push（**共 3 次网络往返**）。

完整规则见 [`rules.md`](rules.md)，锁协议原理与例子见 [`docs/5-concurrency.md`](docs/5-concurrency.md)，最终论文质量规则见 [`docs/6-paper-quality.md`](docs/6-paper-quality.md)。

## 仓库初始化（队长首次操作）

```bash
# 在 GitHub / Gitee 建一个空仓库（不要勾选自动生成 README），拿到地址后：
git remote add origin <远程仓库地址>
git add -A
git commit -m "init: 数模共享工作区骨架 + 写锁协作协议"
git push -u origin main
```

其余两名队员 `git clone` 后即可开工。建议：

- **平台**：国内访问 Gitee 更稳；GitHub 亦可。任选其一，三人统一。
- **大数据**：`files/raw/` 里若有很大的数据集，考虑用 Git LFS，或约定只入库小样本、大数据另传网盘（在 `discussion/decisions.md` 记录）。

---

_本工作区由三人共同维护。修改协作规范前，先在 `discussion/decisions.md` 记录共识。_
