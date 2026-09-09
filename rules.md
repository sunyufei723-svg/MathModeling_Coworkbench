# rules.md — Agent 协作规则（权威协议）

> 本文件是三个 agent 的**完整协作规则**，具有最高优先级。
> codex 通过仓库根的 `AGENTS.md`（入口摘要）指引来读取本文件；Qoder 侧直接读取本文件。
> **开始任何操作前先完整通读本文件，并严格遵守。** 与 `README.md` 或 `AGENTS.md` 冲突时，一律以本文件为准。

---

## 0. 你是谁

- 本仓库由 **3 个人 × 3 个 agent** 协作完成数模国赛。
- 每个 agent 有固定身份：`agent_A` / `agent_B` / `agent_C`（由队员各自认领，全程不变）。
- **全程只用你自己的 ID**。所有加锁、请求、讨论署名都用它。
- 启动第一件事：确认"我是哪个 agent"，不要冒用他人 ID。

---

## 1. 三条铁律（违反会破坏协作，务必遵守）

1. **碰共享资源前必须查锁、按规则加锁**：读 `code/ results/ discussion/ files/` 里的东西前拿**读锁**；改动它们前拿**写锁**。不查锁就动手 = 违规。
2. **只写自己的 `requests/agent_<你>.md`**：请求区文件是单一 owner，别人只读不写，因此**不需要加锁**。
3. **本地 commit ≠ 生效，必须 push**：锁、成果只有在 `git push` 成功后才对其他 agent 可见。永远不要跳过 push。

---

## 2. 目录地图

| 路径 | 用途 | 是否需要锁 |
|---|---|---|
| `discussion/` | 公共讨论：`problem.md` 题目拆解、`ideas.md` 思路、`decisions.md` 决策 | 读→读锁；写→写锁 |
| `requests/` | 每个 agent 的请求/状态板 | **不需要锁**（各自只写自己的文件） |
| `code/` | 代码 | 读→读锁；写→写锁 |
| `results/` | 实验结果、图表、输出 | 读→读锁；写→写锁 |
| `files/` | 原始(`raw/`)/中间(`intermediate/`)/最终(`final/`)文件 | 读→读锁；写→写锁 |
| `locks/` | 锁状态文件，**只能按第 3 节协议编辑** | 由协议管理 |

> **可加锁资源**只有 4 个：`code`、`results`、`discussion`、`files`，分别对应 `locks/code.lock` 等。锁文件仍是**资源级文件**，但每一行可以锁该资源下的具体文件或目录；省略路径时表示锁整个资源目录。

---

## 3. 读写锁协议（核心）

采用**严格读写锁**：读读兼容、写独占。底层用 **git push 的原子性**做串行化——远程仓库会把所有 push 排队，两个并发抢同一范围的写锁只可能一个成功，这就是锁能跨机器生效的原理。

### 3.1 锁文件格式

`locks/<资源>.lock` 是纯文本：

- `#` 开头是注释，空行忽略；
- 每个**活跃持有者**一行：`<模式> <agent> <UTC时间戳> <路径>`
  - 模式：`R` = 读锁（可多个共存）；`W` = 写锁（独占冲突范围）
  - 路径：资源下的具体文件或目录，例如 `code/solver.py`、`code/models/`、`discussion/decisions.md`
- **兼容旧格式**：若一行只有 `<模式> <agent> <UTC时间戳>`，视为锁住整个资源目录（例如 `locks/code.lock` 中省略路径等价于 `code/`）。
- **空文件（或只有注释）= 未加锁**。
- 写锁生效时，只要求**与它路径重叠的范围**里没有任何活跃锁；不同路径可并行。

示例（agent_A 持有 `code/models/solver.py` 的写锁）：
```
# 锁文件：code
W agent_A 2026-09-09T14:30:00Z code/models/solver.py
```
示例（agent_A、agent_B 同时持有不同代码文件的写锁）：
```
# 锁文件：code
W agent_A 2026-09-09T14:30:00Z code/models/solver.py
W agent_B 2026-09-09T14:31:10Z code/plotting/charts.py
```
示例（agent_A、agent_B 同时持有同一讨论文件的读锁）：
```
# 锁文件：discussion
R agent_A 2026-09-09T14:30:00Z discussion/ideas.md
R agent_B 2026-09-09T14:31:10Z discussion/ideas.md
```

**路径规范**：
- 一律使用仓库相对路径，使用 `/` 分隔，不使用 Windows 反斜杠。
- 文件路径写完整文件名，例如 `code/main.py`。
- 目录路径必须以 `/` 结尾，例如 `code/models/`；资源根目录写作 `code/`、`results/`、`discussion/`、`files/`。
- 路径必须位于对应资源目录下：`locks/code.lock` 只能写 `code/...`。

**生成 UTC 时间戳**（三台机器时区可能不同，一律用 UTC）：
- PowerShell：`(Get-Date).ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ssZ")`
- bash：`date -u +%Y-%m-%dT%H:%M:%SZ`

### 3.2 兼容规则表

判断一把新锁是否可拿，分两步：

1. 忽略注释行、空行、以及已过期(超租约)的行。
2. 只比较**路径重叠**的活跃锁；路径不重叠则互不影响。

路径重叠规则：

| 已有路径 | 新路径 | 是否重叠 |
|---|---|---|
| `code/a.py` | `code/a.py` | 是 |
| `code/a.py` | `code/b.py` | 否 |
| `code/models/` | `code/models/solver.py` | 是 |
| `code/models/` | `code/plot.py` | 否 |
| `code/` | `code/任何路径` | 是 |
| 省略路径旧格式 | 该资源下任何路径 | 是 |

路径重叠后的锁兼容规则：

| 你想要的锁 | 重叠范围内有活跃 `R` | 重叠范围内有活跃 `W` | 能否拿 |
|---|---|---|---|
| 读锁 R | 有 | 无 | ✅ 可以（追加一行 R） |
| 读锁 R | 无 | 有 | ❌ 等待 |
| 写锁 W | 有 | 无 | ❌ 等待 |
| 写锁 W | 无 | 有 | ❌ 等待 |
| 写锁 W | 无 | 无 | ✅ 可以（追加一行 W） |

> "**活跃**"= 时间戳未超过租约（见 3.6）。已过期的行按不存在处理。

### 3.3 拿锁（acquire）—— 精确步骤

目标：资源 `R`（code/results/discussion/files 之一），模式 `M`（R 或 W），路径 `P`（仓库相对路径，必须位于资源 `R` 下；锁整个资源时写 `R/`）。

```bash
# 1) 同步到最新锁状态
git pull --rebase

# 2) 打开 locks/R.lock，忽略注释行、空行、以及已过期(超租约)的行，
#    只看与 P 路径重叠的活跃行，按 3.2 兼容表判断：
#      · 不兼容 → 等待 15~30 秒，回到步骤 1 重试（不要硬闯、不要改别人的行）
#      · 兼容   → 继续

# 3) 编辑 locks/R.lock：追加你的一行（顺手删掉已过期的行）
#      读锁： R agent_A 2026-09-09T14:30:00Z code/models/solver.py
#      写锁： W agent_A 2026-09-09T14:30:00Z code/models/solver.py
#      整个资源： W agent_A 2026-09-09T14:30:00Z code/

# 4) 只提交锁文件
git add locks/R.lock
git commit -m "lock: agent_A acquire W on code/models/solver.py"

# 5) 推送——锁在这一刻才真正生效
git push
#   · push 成功 → 拿锁成功，可以开始对 P 读/写
#   · push 被拒(non-fast-forward，说明有人抢先动了锁) → 见 3.4 回退后重试
```

### 3.4 push 被拒的回退（安全，不丢你其它工作）

```bash
git reset --soft HEAD~1                        # 撤销这次“锁提交”，其它提交/改动不受影响
git restore --staged --worktree locks/R.lock   # 把锁文件还原到提交前
git pull --rebase                              # 拉取对方刚推上来的锁状态
# 回到 3.3 步骤 2 重新判断（对方可能已加了与你冲突的锁）
```

> 这套回退**只碰锁文件**，你未提交的其它改动、未推送的其它提交都不会丢。

### 3.5 释放锁（release）

```bash
# 干完活，先把成果提交并推送（仍在你持锁期间，别人改不了 P）
git add -A
git commit -m "code: <说明>"     # 或 results:/files:/discussion:
git pull --rebase
git push

# 再释放锁
git pull --rebase
# 编辑 locks/R.lock，删掉你自己那一行（匹配自己的 agent、模式、时间戳、路径）
git add locks/R.lock
git commit -m "lock: agent_A release code/models/solver.py"
git push
# push 若被拒：用 3.4 的软回退，再重做“删自己那行 + 提交 + 推送”
```

> **务必释放**。用完不放锁会阻塞对应路径范围内的协作（虽有租约兜底，但别依赖它）。

### 3.6 租约与抢占失效锁（防死锁兜底）

- 每个锁行带时间戳，**租约 30 分钟**：`现在(UTC) - 时间戳 > 30 分钟` 即视为**失效**。
- 失效的行在你拿锁时**当作不存在**，可在你的 acquire 提交里顺手删除并抢占。
- **长时间持锁要续租**：每 15~20 分钟更新一次你那行的时间戳（pull → 改时间戳 → commit → push，push 被拒走 3.4）。否则会被别人当失效抢走。
- 抢占别人的"疑似失效"写锁前，最好先在 `requests/` 里 @ 一下对方确认，避免误抢正在续租的操作。

### 3.7 同时需要多个资源或多个路径（防死锁）

- 需要同时持有多把锁时，**一律按固定顺序申请**：`code → discussion → files → results`（字母序）。
- 同一资源内需要多个路径时，先锁更上层/更大的目录；如果都是同级文件，按路径字母序申请。
- 绝不允许“A 拿着 code 等 results、B 拿着 results 等 code”这种交叉等待。
- 释放顺序不限。能只拿具体文件就别锁整个目录；能只拿一把就别拿多把。

---

## 4. git 操作规范

- **随时同步**：开始工作前、push 前，先 `git pull --rebase`，保持线性历史。
- **及时 push**：commit 后尽快 push，减少与他人分叉。
- **提交信息前缀**：`lock:`(锁操作) / `code:` / `results:` / `files:` / `discussion:` / `req:`(请求板) / `docs:` / `wip:`。
- **非锁文件冲突**：`git pull --rebase` 若在 code/results 等文件上冲突，说明有人在你没拿写锁时改了同一文件——先解决冲突（尽量保留双方成果），并反思是否漏加了锁。
- **锁文件冲突**：`.lock` 文件出现冲突时，不要手工硬拼；执行 `git rebase --abort`，重新 `git pull --rebase`，再按 3.3 重新走拿锁流程。
- **禁止 `git push --force` / `--force-with-lease` 到 `main`**。会毁掉别人的工作。

---

## 5. 请求机制（requests/）

- 每个 agent 只写自己的 `requests/agent_<你>.md`，**不需要锁**（单一 owner，天然无冲突）。
- **需要别人做事**：在**你自己的**文件里追加一行，`@` 目标 agent：
  ```
  - [2026-09-09T14:30Z] @agent_B 请把 results/fig3.png 重画成 300dpi  状态:待认领
  ```
- **发现指派给自己的请求**：定期读三个 `requests/*.md`（读请求区**不需要锁**），看到 `@你` 且"待认领"的，就在**你自己的**文件里登记认领与进度。
- **完成后回报**：也在**你自己的**文件里写一行通知发起方（例如 `@agent_A 你要的高清图已完成，见 results/fig3.png`），发起方轮询得知。**不要去改对方的文件。**

---

## 6. 讨论区规范（discussion/）

- 读讨论区：拿 `discussion/` 或具体讨论文件的读锁；写讨论区：拿对应路径的写锁（见第 3 节）。
- **只追加，不改写他人条目**。每条署名 + UTC 时间戳：
  ```
  ## [agent_A 2026-09-09T14:30Z] 建议用元胞自动机建模车流
  理由：……
  ```
- `decisions.md` 记录**已定决策**：决策内容 + 理由 + 参与者 + 时间。定了就别反复推翻，要改需在此说明原因。

---

## 7. 禁止事项（红线）

- ❌ 不查锁 / 不加锁就读写 `code/ results/ discussion/ files/`。
- ❌ 手动修改或删除**别人未过期**的锁行（只能删已过期的，且在你的 acquire 提交里）。
- ❌ 只 `commit` 不 `push` 就以为拿了锁 / 发布了成果。
- ❌ 写别人的 `requests/agent_X.md`。
- ❌ `git push --force` 到 `main`。
- ❌ 冒用他人 agent ID。
- ❌ 把大数据集/临时文件/编译产物提交进仓库（见 `.gitignore`）。

---

## 8. 完整示例

### 示例一：读一段代码（读锁）
```bash
git pull --rebase
# 看 locks/code.lock：没有与 code/models/solver.py 重叠的活跃 W 行 → 可以拿读锁
# 编辑 locks/code.lock 追加： R agent_A <现在UTC> code/models/solver.py
git add locks/code.lock
git commit -m "lock: agent_A acquire R on code/models/solver.py"
git push                       # 成功 → 拿到读锁
# ……阅读 code/models/solver.py……
# 读完释放：删掉自己那行
git pull --rebase
git add locks/code.lock
git commit -m "lock: agent_A release code/models/solver.py"
git push
```

### 示例二：改代码并产出结果（写锁 + 顺序）
```bash
# 需要同时改 code/models/solver.py 和写 results/run1/ → 按顺序 code → results 申请写锁
git pull --rebase
# locks/code.lock 中没有与 code/models/solver.py 重叠的活跃锁 → 追加： W agent_A <现在UTC> code/models/solver.py
git add locks/code.lock ; git commit -m "lock: agent_A acquire W on code/models/solver.py" ; git push
# 再拿 results/run1/ 写锁（同样 pull→判断路径重叠→写 W→commit→push）
# ……改 code/models/solver.py、把输出写进 results/run1/……（超过 15~20 分钟记得续租两把锁）
git add -A ; git commit -m "code: 实现求解器并输出结果" ; git pull --rebase ; git push
# 释放（先 results 后 code 亦可，顺序不限）：分别删自己那行 → commit → push
```

---

_最后更新：2026-09-09。修改本协议前，先在 `discussion/decisions.md` 记录共识，再改本文件并通知全部 agent。_
