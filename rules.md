# rules.md — Agent 协作规则（简洁权威版）

> 三个 agent 的协作规则，**最高优先级**；与 `README.md` / `AGENTS.md` 冲突一律以本文件为准。
> 本文件是**简洁版**：只讲 5 层结构 + 核心流程 + 铁律 + 每层速览。每层末尾给出 `docs/` 详解路径——**看不懂就去读对应 docs 文件**（完整 git 命令、原理、例子都在那里）。
> 开始任何操作前：① 读本机 `identity.md` 确认「我是谁」；② 通读本文件；③ 需要细节按路径读 `docs/`。

---

## 项目结构：5 层

| 层 | 目录 / 文件 | 一句话职责 | 详解 |
|---|---|---|---|
| **1 工作规范** | `identity.md` `rules.md` `AGENTS.md` | 你是谁、铁律、git 规范、红线 | [`docs/1-work-norms.md`](docs/1-work-norms.md) |
| **2 通信层** | `requests/` | agent 间异步通信：状态板、@请求、认领回报 | [`docs/2-communication.md`](docs/2-communication.md) |
| **3 知识层** | `discussion/` | 共享知识：题目拆解 / 思路 / 决策（只追加） | [`docs/3-knowledge.md`](docs/3-knowledge.md) |
| **4 执行层** | `code/` `results/` `files/` | 工作产物：代码 / 结果 / 原始·中间·最终文件 | [`docs/4-execution.md`](docs/4-execution.md) |
| **5 并发控制层** | `locks/` | 写锁协议：串行化并发写、防覆盖、防死锁 | [`docs/5-concurrency.md`](docs/5-concurrency.md) |

> 5 层是**概念分层**，物理目录不变。可加锁资源只有 4 个：`code` / `results` / `discussion` / `files`（对应 `locks/*.lock`）；`requests/` 单一 owner 免锁；根协议文件（rules.md/AGENTS.md/README.md/docs/）用整把 discussion 锁代理保护。

---

## 核心流程（最重要，务必背下来）

**本仓库只有写锁 W，读取一律免锁。** 一次操作分「读」「写」两条路径：

### 读共享文件（0 锁、0 push）
1. `git pull --rebase`
2. 查 `locks/*.lock`：目标路径有无**活跃 W 锁**？有 → 暂缓读（等对方 push 完再 pull 最新）；无 → 直接读，不加锁、不 push
3. 顺带读 `requests/*.md` 看有无 `@你`

### 写共享文件（2 次 push，共 3 次网络往返）
1. **pull**：`git pull --rebase`（查远程 + 查队友 requests / locks）
2. **状态 + 锁 → 一个 commit → push**：在 `requests/agent_<你>.md` 写「正在做」+ 在 `locks/<资源>.lock` 追加 `W agent_<你> <UTC> <路径>` → `git add` 这两个文件 → commit → **push**（成功 = 状态广播 + 锁生效）
3. **本地写内容**（锁 + 30 分钟租约保护；将超时则续租）
4. **内容 + 解锁 + 状态 → 一个 commit → push**：删掉自己那行锁 + 状态改回空闲/进度 → `git add -A` → commit → **push**（被拒则 `git pull --rebase --autostash` 后重 push）

> ⚠️ **顺序铁律：先 push「状态 + 锁」，再写内容，不可颠倒。** 完整 git 命令、push 被拒的回退、端到端例子见 [`docs/5-concurrency.md`](docs/5-concurrency.md)。

---

## 三条铁律

1. **写共享资源前查锁 + 加写锁 W**：改 `code/ results/ discussion/ files/` 前拿写锁；**读取免锁**，但先查目标路径有无活跃 W 锁，有则暂缓读。不查锁就写 = 违规。
2. **只写自己的 `requests/agent_<你>.md`**：单一 owner，别人只读，免锁。
3. **commit ≠ 生效，必须 push**：锁和成果只有 `git push` 成功后才对其他 agent 可见。

---

## 最终论文质量规则 → [`docs/6-paper-quality.md`](docs/6-paper-quality.md)

- **参考文献必需**：正文/附录中出现的算法、数值格式、模型检验、敏感性/不确定性方法、数据来源、物性公式和非原创图表，都必须给可核验引用；禁止编造文献。
- **只写论文该写的内容**：论文写建模假设、方程、离散格式、参数、验证、结果、局限；不得写 `.gitignore`、本机附件、仓库路径、agent 分工、锁、commit、谁能跑代码等工程协作细节。
- **术语和数值统一**：同一模型/算法/变量/单位全篇只用一个名称；摘要、正文、表格、图、结论、附录中的主结果必须一致，旧口径只能作为明确标注的对照。
- **证据强度匹配表述**：有直接计算/检验才能写“表明/验证”；推断性解释用“说明/提示/可能”；不写“首次、最优、完全、显著”等无证据大词。
- **最终提交前必查**：引用完整性、图表编号、公式符号、单位量纲、结果复现命令、限制条件、错别字、排版和专业性；检查清单见详细版。

---

## 5 层规则速览（每层详情见对应 docs）

### 第 1 层 · 工作规范 → [`docs/1-work-norms.md`](docs/1-work-norms.md)
- **身份**：全程只用 `agent_A/B/C` 之一（读本机 `identity.md` 确认），不冒用。
- **git**：单 `main`；`pull --rebase` 保线性；提交前缀 `lock:/code:/results:/files:/discussion:/req:/docs:/wip:`；禁 `push --force` 到 main。
- **红线**：不 force push；不改/删别人未过期锁行；不只 commit 不 push；不写别人的 requests；不冒用 ID；不提交大数据/产物。

### 第 2 层 · 通信层（requests/）→ [`docs/2-communication.md`](docs/2-communication.md)
- 每个 agent 只写自己的 `agent_<你>.md`，别人只读，**免锁**。
- **状态优先**：写共享内容前，先把「正在做」写进状态板并与加锁合并 push；做完改回空闲。绝不先写内容后补状态。
- 请别人做事：在自己文件「发出请求 · 活跃」区 `@目标`（不改对方文件）；请求区分「活跃 / 已闭环归档」两段——**活跃只留未闭环项（简短），归档保留完整详情（平时不翻、出错时才查解决办法，D10）**。
- **闭环靠发起方追踪（D9）**：谁发请求谁负责核验闭环——主动查对方提交/结果、更新状态、移入归档，**不依赖对方回报**；对方认领/回报为自愿加分项（可在「最近完成」尾带 `@发起agent 已闭环`）。

### 第 3 层 · 知识层（discussion/）→ [`docs/3-knowledge.md`](docs/3-knowledge.md)
- `problem.md` 题目拆解 / `ideas.md` 思路 / `decisions.md` 决策。
- **只追加、不改他人条目**；每条署名 + UTC。
- `decisions.md` 记已定决策（决策/理由/参与者/影响 四段式）；**改协议先在此记共识**再改。
- 读免锁（查 W 锁）；写拿 discussion 写锁。

### 第 4 层 · 执行层（code/ results/ files/）→ [`docs/4-execution.md`](docs/4-execution.md)
- `code/` 代码 / `results/` 结果图表 / `files/`：`raw/` 原始(只读为主) `intermediate/` 中间 `final/` 最终。
- 读免锁（查 W 锁）；写拿对应资源写锁；优先锁具体文件/目录。
- 大数据 / 临时 / 编译产物**不入库**（见 `.gitignore`）。

### 第 5 层 · 并发控制层（locks/）→ [`docs/5-concurrency.md`](docs/5-concurrency.md)
- **只有写锁 W**，独占其路径范围；不同路径可并行。读取免锁（git commit 是原子快照，读不到半成品）。
- 锁行：`W <agent> <UTC> <路径>`；省略路径 = 锁整个资源。
- **push 原子性 = 锁跨机器生效原理**：push 成功才算拿到；被拒 → `reset --soft HEAD~1` + `restore --staged --worktree <lock>` + `pull --rebase --autostash` 回退重判。
- **租约 30 分钟**防死锁；多锁按 `code → discussion → files → results` 顺序申请。
- 锁文件冲突不硬拼：`rebase --abort` → 重走拿锁。

---

_最后更新：2026-09-11（D11：新增最终论文写作与质量规则）。修改本协议前，先在 `discussion/decisions.md` 记录共识，再改本文件并通知全部 agent。_
