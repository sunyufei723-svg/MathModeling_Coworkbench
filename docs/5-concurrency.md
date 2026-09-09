# 第 5 层 · 并发控制层详解（locks/）

> 本文件展开 `rules.md`「第 5 层 并发控制」的**完整细节**：原理、锁文件格式、兼容判断、拿锁/放锁/回退/续租/多锁顺序、锁冲突处理、端到端例子。
> 简洁规则见 [`rules.md`](../rules.md)；这里看不懂就逐节读。**只有写锁 W，读取一律免锁。**

---

## 5.1 原理：为什么 git 能做跨机器的锁

- git **没有**跨网络的原子 check-and-set。朴素思路「读 lock 文件 → 为空就写自己名字 → 提交」**无效**：两个 agent 会在彼此的 push 到达前都读到锁为空、都以为拿到了锁，push 时冲突或互相覆盖，lock 文件沦为君子协定。
- 但 **`git push` 是原子的**：远程仓库把所有 push 排队，非快进（non-fast-forward）的 push 会被拒绝。
- 于是：**push 成功 = 拿锁成功**；**push 被拒 = 有人抢先**，回退重新判断（见 5.7）。两个并发抢同一路径写锁的 push，只可能一个成功。
- 这是锁能跨机器生效的**唯一基础**——一切以远程 push 的成败为准，本地 commit 不算数。

## 5.2 为什么读取不需要锁（废除读锁 R 的理由）

- git 以 **commit 为原子快照**：任何人 pull 到的都是某个完整 commit 的版本，**绝不会读到「写了一半」的文件**——写方的改动是在释放锁那一步（5.6）随解锁一次性原子 push 的。
- 因此「读锁防止读到中间态」在 git 模型下本就多余，予以**废除**。
- 读取唯一要注意的是**别读到即将过时的旧版**：若目标路径正被别人的活跃 `W` 锁盖住，说明对方正在改、新内容还没 push，你此刻 pull 到的是旧版——**先别读**，等对方释放后再 pull 最新。
- 所以读取规则一句话：**查目标路径有无活跃 W 锁；有则暂缓，无则直接读**（0 锁、0 push）。

## 5.3 锁文件格式

`locks/<资源>.lock` 是纯文本，四个资源各一个：`code.lock` / `results.lock` / `discussion.lock` / `files.lock`。

- `#` 开头是注释，空行忽略；
- 每个**活跃写锁持有者**一行：`W <agent> <UTC时间戳> <路径>`
  - `W` = 写锁（独占其路径范围）
  - 路径：资源下的具体文件或目录，例如 `code/solver.py`、`code/models/`、`discussion/decisions.md`
- **省略路径**（一行只有 `W <agent> <UTC时间戳>`）= 锁住**整个资源目录**（如 `locks/code.lock` 中省略路径等价于锁 `code/`）。根协议文件（rules.md/AGENTS.md/README.md/docs/）不属于四个资源，约定用**整把 discussion 写锁**（省略路径）作代理保护。
- **空文件（或只有注释）= 未加锁**。
- 一条写锁生效时，只要求**与它路径重叠的范围**里没有其它活跃写锁；不同路径可并行。

示例（agent_A 持有 `code/models/solver.py` 的写锁）：
```
# 锁文件：code
W agent_A 2026-09-09T14:30:00Z code/models/solver.py
```
示例（agent_A、agent_B 同时持有不同代码文件的写锁，路径不重叠 → 合法并行）：
```
# 锁文件：code
W agent_A 2026-09-09T14:30:00Z code/models/solver.py
W agent_B 2026-09-09T14:31:10Z code/plotting/charts.py
```

**路径规范**：
- 一律用仓库相对路径，`/` 分隔，不用 Windows 反斜杠。
- 文件写完整名，如 `code/main.py`；目录必须以 `/` 结尾，如 `code/models/`；资源根写作 `code/`、`results/`、`discussion/`、`files/`。
- 路径必须位于对应资源目录下：`locks/code.lock` 只能写 `code/...`。

**生成 UTC 时间戳**（三台机器时区可能不同，一律用 UTC）：
- PowerShell：`(Get-Date).ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ssZ")`
- bash：`date -u +%Y-%m-%dT%H:%M:%SZ`

## 5.4 兼容规则（判断能否拿写锁）

分两步：
1. 忽略注释行、空行、以及已过期（超租约，见 5.8）的行。
2. 只比较**路径重叠**的活跃写锁；路径不重叠则互不影响、可并行。

路径重叠规则：

| 已有路径 | 新路径 | 是否重叠 |
|---|---|---|
| `code/a.py` | `code/a.py` | 是 |
| `code/a.py` | `code/b.py` | 否 |
| `code/models/` | `code/models/solver.py` | 是 |
| `code/models/` | `code/plot.py` | 否 |
| `code/` | `code/任何路径` | 是 |
| 省略路径 | 该资源下任何路径 | 是 |

路径重叠后的写锁规则（只剩一种锁，规则极简）：

| 你想要的锁 | 重叠范围内有活跃 `W` | 能否拿 |
|---|---|---|
| 写锁 W | 无 | ✅ 可以（追加一行 W） |
| 写锁 W | 有 | ❌ 等待（等对方释放，或租约过期后抢占） |

> 「**活跃**」= 时间戳未超过租约（见 5.8）。已过期的行按不存在处理，可在你的 acquire 提交里顺手删除并抢占。

## 5.5 拿写锁（acquire）—— 与状态板合并成一个 commit

目标：资源 `R`（code/results/discussion/files 之一），路径 `P`（仓库相对路径，必须位于 `R` 下；锁整个资源写 `R/`）。按 `rules.md` 核心流程「写路径」第 2 步，**锁行与状态板合并成一个 commit**：

```bash
# 1) 同步到最新锁状态
git pull --rebase

# 2) 打开 locks/R.lock，忽略注释/空行/已过期行，
#    只看与 P 路径重叠的活跃 W 行，按 5.4 判断：
#      · 有重叠的活跃 W → 等待 15~30 秒，回到步骤 1 重试（不硬闯、不改别人的行）
#      · 无             → 继续

# 3) 编辑 locks/R.lock：追加你的一行（顺手删掉已过期的行）
#      W agent_A 2026-09-09T14:30:00Z code/models/solver.py
#      锁整个资源： W agent_A 2026-09-09T14:30:00Z code/
#    同时编辑 requests/agent_A.md：「正在做」写下将做的事

# 4) 锁行 + 状态板 放进同一个 commit
git add locks/R.lock requests/agent_A.md
git commit -m "lock: agent_A acquire W on code/models/solver.py + status"

# 5) 推送——锁在这一刻才真正生效
git push
#   · push 成功 → 拿锁成功，可以开始写 P
#   · push 被拒（non-fast-forward，有人抢先动了锁）→ 见 5.7 回退后重试
```

## 5.6 写内容 + 释放锁（release）—— 合并成一次 push

在锁 + 租约保护下写完内容后，**把「内容 + 删锁行 + 改状态」放进同一个 commit 一次 push**：

```bash
# 1) 写完内容（本地）
# 2) 编辑 locks/R.lock，删掉你自己那一行（匹配自己的 agent/时间戳/路径）
# 3) 编辑 requests/agent_<你>.md，状态改为进度或删回「空闲」
git add -A                                     # 内容 + 锁文件 + 状态板一起
git commit -m "code: <说明>（含释放锁 + 状态更新）"
git push
#   · push 被拒（期间有人推了新提交）→ git pull --rebase --autostash 后重 push；
#     因你持 W 锁、目标路径不会被人改，rebase 不会在内容上冲突
```

> **务必释放**（删掉自己那行并 push）。内容与解锁在同一次 push 原子生效，不存在「内容已发布但锁没放」或「锁放了但内容没发布」的中间态。用完不放锁会阻塞对应路径的协作（虽有租约兜底，但别依赖它）。

## 5.7 push 被拒的回退（安全，不丢你其它工作）

拿锁的 commit **同时含锁文件和状态板**，回退用 `--autostash` 兜住工作区：

```bash
git reset --soft HEAD~1                        # 撤销这次「锁+状态」提交，改动退回暂存区
git restore --staged --worktree locks/R.lock   # 只还原锁文件（丢弃你的加锁行）；状态板改动保留
git pull --rebase --autostash                  # 拉对方刚推上来的锁状态；autostash 自动兜起暂存改动再恢复
# 回到 5.5 步骤 2 重新判断（对方可能已加了与你冲突的锁），重新写锁行 → commit → push
```

> 状态板 `requests/agent_<你>.md` 是单一 owner、免锁，**永不与人冲突**；冲突只可能来自锁文件。回退只丢弃你那条加锁行，状态改动和其它未提交工作都不会丢。

## 5.8 租约与抢占失效锁（防死锁兜底）

- 每条锁行带时间戳，**租约 30 分钟**：`现在(UTC) - 时间戳 > 30 分钟` 即视为**失效**。
- 失效的行在你拿锁时**当作不存在**，可在你的 acquire 提交里顺手删除并抢占。
- **长时间持锁要续租**：每 15~20 分钟更新一次你那行的时间戳（pull → 改时间戳 → commit → push，push 被拒走 5.7）。否则会被别人当失效抢走。
- 抢占别人的「疑似失效」写锁前，最好先在 `requests/` 里 @ 一下对方确认，避免误抢正在续租的操作。

## 5.9 同时需要多个资源或多个路径（防死锁）

- 需要同时持有多把写锁时，**一律按固定顺序申请**：`code → discussion → files → results`（字母序）。
- 同一资源内需要多个路径时，先锁更上层/更大的目录；如果都是同级文件，按路径字母序申请。
- 绝不允许「A 拿着 code 等 results、B 拿着 results 等 code」这种交叉等待。
- 释放顺序不限。能只拿具体文件就别锁整个目录；能只拿一把就别拿多把。

## 5.10 锁文件冲突处理

- `.lock` 文件出现 rebase 冲突时，**不要手工硬拼**：执行 `git rebase --abort`，重新 `git pull --rebase`，再按 5.5 重新走拿锁流程。
- 非锁文件（code/results 等）冲突，说明有人在你没拿写锁时改了同一文件——先解决冲突（尽量保留双方成果），并反思是否漏加了锁。

## 5.11 端到端例子

### 例子一：读一段代码（免锁，只查写锁，0 push）
```bash
git pull --rebase                       # 前置① 查远程
# 前置② 查 locks/code.lock：目标 code/models/solver.py 有没有被活跃 W 行盖住？
#   · 有 W 锁 → 有人正在改，先别读，等释放后再 pull 最新
#   · 无 W 锁 → 直接读，不加锁、不 push
cat code/models/solver.py               # 直接读
```
> 读取全程 **0 push、0 锁**：git commit 是原子快照，读到的永远是完整版本。

### 例子二：改代码并产出结果（写锁 + 合并 push，共 3 次网络往返）
```bash
# 需要同时改 code/models/solver.py 和写 results/run1/ → 按 code → results 顺序申请两把写锁
git pull --rebase                       # 网络① 查远程 + 查队友（requests、locks）
# 状态 + 两把锁 合并成一个 commit：
#   requests/agent_A.md「正在做: 改 solver + 产出 run1」
#   locks/code.lock    追加 W agent_A <现在UTC> code/models/solver.py
#   locks/results.lock 追加 W agent_A <现在UTC> results/run1/
git add requests/agent_A.md locks/code.lock locks/results.lock
git commit -m "lock: agent_A acquire W on solver.py + run1/ + status"
git push                                # 网络② 成功 = 状态广播 + 两把锁生效
# ……本地改 code/models/solver.py、把输出写进 results/run1/……（超 15~20 分钟记得续租两把锁）
# 内容 + 删两把锁行 + 状态改回空闲，合并成一个 commit：
git add -A
git commit -m "code: 实现求解器并输出结果（含释放锁 + 状态更新）"
git push                                # 网络③ 被拒则 git pull --rebase --autostash 后重 push
```
> 全程只有 **3 次网络往返**（1 pull + 2 push）：锁的 acquire/release 都并入相邻的 push，不再单独占用往返。
