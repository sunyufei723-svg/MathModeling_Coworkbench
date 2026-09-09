# decisions.md — 已定决策记录

> 共享文件：读需 `discussion` 读锁，写需 `discussion` 写锁（见 rules.md 第 3 节）。
> **只追加。** 一旦定案，全队按此执行；要推翻旧决策，追加新条目并说明原因，不要删旧的。
> 每条格式：`## D<编号> [时间戳UTC] 决策标题` + 决策内容 / 理由 / 参与者 / 影响。

---

## D0 [2026-09-09T00:00Z] 采用「严格读写锁 + 单一 owner 请求区」协作方案
- **决策**：共享区（code/results/discussion/files）读写均按 rules.md 第 3 节加锁；requests/ 各写各的、不加锁。
- **理由**：三人各自电脑、agent 自动执行 git；用 `git push` 原子性实现跨机器读写锁，防并发覆盖。
- **参与者**：全体（待定认领 agent_A/B/C）。
- **影响**：所有 agent 必须遵守 rules.md；写锁租约 30 分钟防死锁。

## D1 [2026-09-09T00:00Z] AGENTS.md 作入口、完整规则移入 rules.md
- **决策**：`AGENTS.md` 精简为「入口摘要 + 三条铁律 + 导向 rules.md」；完整权威协议移到 `rules.md`。codex 自动读仓库根的 `AGENTS.md`，据此打开并遵守 `rules.md`。
- **理由**：codex 的发现顺序是「全局 ~/.codex/ → 仓库根 → 子目录」，只自动读 `AGENTS.md`。把指路写进**仓库里的** `AGENTS.md`，随 git 共享、三人零配置；不采用「每台机器手配 ~/.codex/config.toml 的 fallback 文件名」——那种不入库、易漏配。
- **参与者**：全体。
- **影响**：以后改协议只改 `rules.md`，`AGENTS.md` 保持稳定；冲突一律以 `rules.md` 为准。

<!-- 在下方追加 D2、D3 …… -->
