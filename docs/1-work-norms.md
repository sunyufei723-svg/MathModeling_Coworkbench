# 第 1 层 · 工作规范详解

> 展开 `rules.md`「第 1 层 工作规范」：身份、协议文件与优先级、git 操作规范、红线。
> 简洁规则见 [`rules.md`](../rules.md)。

---

## 1.1 身份（你是谁）

- 本仓库由 **3 个人 × 3 个 agent** 协作完成数模国赛（1 个 Qoder + 2 个 codex，各自电脑）。
- 每个 agent 有固定身份：`agent_A` / `agent_B` / `agent_C`，由队员各自认领，**全程不变**。
- 本机身份写在本机 `identity.md`（已被 `.gitignore` 忽略、**不入库**）：三台机器各自维护自己的，**切勿提交或推送**，否则互相覆盖身份。
- 启动第一件事：读 `identity.md` 确认「我是哪个 agent」，**不冒用他人 ID**。所有加锁、请求、讨论署名都用自己的 ID。
- 谁认领哪个身份，建议在 `discussion/decisions.md` 记一条，全队对齐。

## 1.2 协议文件与优先级

| 文件 | 角色 | 谁读 |
|---|---|---|
| `AGENTS.md` | 极简入口（摘要 + 导向 rules.md） | codex 自动读取 |
| `rules.md` | **简洁权威协议（最高优先级）** | 所有 agent 主读 |
| `docs/1~6-*.md` | 各层详细解释 + 论文质量规则 + 例子 | 看不懂简洁版时按路径读 |
| `README.md` | 人看的总览 / 5 层导航 | 队员（人） |
| `identity.md` | 本机身份（不入库） | 本机 agent 启动时 |

- 冲突时**一律以 `rules.md` 为准**。
- 改协议前先在 `discussion/decisions.md` 记录共识，再改，并通知全部 agent（见 `docs/3-knowledge.md`）。
- 最终论文写作与质量规则见 `docs/6-paper-quality.md`；修改 `files/final/` 论文时必须遵守。

## 1.3 git 操作规范

- **单 `main` 分支**协作。
- **随时同步**：开工前、push 前先 `git pull --rebase`，保持线性历史。
- **及时 push**：commit 后尽快 push，减少与他人分叉。
- **提交信息前缀**：`lock:`(锁操作) / `code:` / `results:` / `files:` / `discussion:` / `req:`(请求板) / `docs:` / `wip:`。
- **非锁文件冲突**：`git pull --rebase` 若在 code/results 等文件上冲突，说明有人在你没拿写锁时改了同一文件——先解决冲突（尽量保留双方成果），并反思是否漏加了锁。
- **锁文件冲突**：`.lock` 冲突不要手工硬拼；`git rebase --abort` → 重新 `git pull --rebase` → 重走拿锁流程（详见 `docs/5-concurrency.md` 5.10）。
- **禁止 `git push --force` / `--force-with-lease` 到 `main`**——会毁掉别人的工作。

## 1.4 红线（禁止事项）

- ❌ 写 `code/ results/ discussion/ files/` 前不查锁 / 不加写锁 W。（读取免锁，但目标被活跃 W 锁盖住时应暂缓读）
- ❌ 手动修改或删除**别人未过期**的锁行（只能删已过期的，且在你的 acquire 提交里）。
- ❌ 只 `commit` 不 `push` 就以为拿了锁 / 发布了成果。
- ❌ 写别人的 `requests/agent_X.md`。
- ❌ `git push --force` 到 `main`。
- ❌ 冒用他人 agent ID。
- ❌ 把大数据集 / 临时文件 / 编译产物提交进仓库（见 `.gitignore` 与 `docs/4-execution.md`）。
