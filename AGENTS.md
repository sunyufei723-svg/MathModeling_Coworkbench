# AGENTS.md — 入口（codex 会自动读取本文件）

> ⚠️ **完整协作规则在 [`rules.md`](rules.md)**（简洁权威版，最高优先级）。对仓库做任何操作前，必须先读它。
> 本文件只是极简入口；如与 `rules.md` 冲突，一律以 `rules.md` 为准。

## 第一步（必做）

1. 读本机 `identity.md`，确认「我是 `agent_A` / `agent_B` / `agent_C` 中的哪一个」，全程只用这个身份。
2. 完整读 [`rules.md`](rules.md)：5 层结构、核心流程、三条铁律都在里面。
3. `rules.md` 某层看不懂 → 按它给的路径读 `docs/1~5-*.md`（详细解释 + 完整 git 命令 + 例子）。

## 项目 5 层（概念分层，物理目录不变）

1. **工作规范**（`identity.md`/`rules.md`/`AGENTS.md`）· 2. **通信层**（`requests/`）· 3. **知识层**（`discussion/`）· 4. **执行层**（`code/` `results/` `files/`）· 5. **并发控制层**（`locks/`）

## 核心流程（只有写锁 W，读取免锁）

- **读共享文件**：`git pull --rebase` → 查目标路径有无**活跃 W 锁**（有则暂缓读、无则直接读）→ **0 锁、0 push**。
- **写共享文件**：`pull` →〔状态 + 锁〕合并一个 commit `push` → 本地写内容 →〔内容 + 解锁 + 状态〕合并一个 commit `push`。

## 三条铁律

1. **写共享资源前查锁 + 加写锁 W**：改 `code/ results/ discussion/ files/` 前拿写锁；读取免锁，但先查目标路径有无活跃 W 锁，有则暂缓读。
2. **只写自己的 `requests/agent_<你>.md`**：单一 owner，别人只读，免锁。
3. **commit ≠ 生效，必须 push**：锁和成果只有 push 成功后才对其他 agent 可见。

> 各层详解：工作规范 [`docs/1-work-norms.md`](docs/1-work-norms.md) · 通信 [`docs/2-communication.md`](docs/2-communication.md) · 知识 [`docs/3-knowledge.md`](docs/3-knowledge.md) · 执行 [`docs/4-execution.md`](docs/4-execution.md) · 并发控制 [`docs/5-concurrency.md`](docs/5-concurrency.md)。
