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

## 1. 开工前置 + 三条铁律（违反会破坏协作，务必遵守）

### 1.0 开工前置（每次动手前，严格按序：先查 → 再报状态+加锁 → 后写内容）

本仓库只有 **写锁（W）**，没有读锁——**读取任何共享文件都不加锁**（原因见 3.0）。据此，一次操作分「读」和「写」两条路径：

**A. 只是读取共享文件（code/results/discussion/files 里的内容）——0 锁、0 push：**

1. **查远程**：`git pull --rebase` 同步到最新。
2. **查目标文件有没有被写锁盖住**：读 `locks/*.lock`，看目标路径是否落在某条活跃 `W` 行的路径范围内（判重叠见 3.2）。
   - **有 W 锁** → 有人正在改它、新内容还没 push，此刻读到的是**即将过时的旧版**：**先别读**，等对方释放后再 pull 到最新版读。
   - **无 W 锁** → 直接读，**不加任何锁、不 push**。
3. 顺带读 `requests/*.md` 看有无 `@你` 的新请求、队友状态变化。

> 读取路径**零 push、零锁**：git 以 commit 为原子快照，你 pull 到的永远是完整版本，不会读到“写了一半”的文件，所以读锁本就多余（详见 3.0）。

**B. 要写共享文件（改动 code/results/discussion/files，或改本协议文件）——共 3 次网络往返：**

1. **查远程 + 查队友**（网络① pull）：`git pull --rebase`；读 `requests/*.md`（有无 `@你`）、`locks/*.lock`（目标路径是否已被别人活跃 `W` 锁占住）。
2. **报状态 + 加锁 → 一个 commit → push**（网络② push）：
   - 在**你自己的** `requests/agent_<你>.md`「当前状态 · 正在做」写下将做的事（如 `改 solver → code/models/solver.py`）；
   - 在 `locks/<资源>.lock` 追加写锁行 `W agent_<你> <UTC> <路径>`（判可拿见 3.2、步骤见 3.3）；
   - `git add requests/agent_<你>.md locks/<资源>.lock` → `git commit` → **`git push`**。push 成功 = 状态已广播 + 锁已生效。
3. **写内容**（本地，0 网络）：在第 2 步的锁 + 30 分钟租约保护下改文件；将超时则续租（3.6）。
4. **解锁 + 改状态 + 提交内容 → 一个 commit → push**（网络③ push）：
   - 删掉 `locks/<资源>.lock` 里你自己那行；把 `requests/agent_<你>.md` 状态改为进度或删回「空闲」；
   - `git add -A` → `git commit` → **`git push`**；
   - push 若被拒（期间有人推了新提交）→ 走 3.4 回退（`git pull --rebase --autostash` 后重 push）；因你持 W 锁、目标路径不会被人改，rebase 不会在内容上冲突。

> ⚠️ **顺序铁律：先 push「状态 + 锁」，再写内容——不可颠倒。** 内容与解锁合并到最后一次 push，写操作全程只有 **2 次 push**（读操作 0 次）。先把内容写了才补状态，队友的前置检查看不到你的意图，等于放弃协调、极易撞车。

### 1.1 三条铁律

1. **写共享资源前必须查锁、加写锁（W）**：改动 `code/ results/ discussion/ files/` 前拿**写锁**；**读取免锁**，但要先查目标路径有没有被活跃 `W` 锁盖住，有则暂缓读（见 1.0-A）。不查锁就写 = 违规。
2. **只写自己的 `requests/agent_<你>.md`**：请求区文件是单一 owner，别人只读不写，因此**不需要加锁**。
3. **本地 commit ≠ 生效，必须 push**：锁、成果只有在 `git push` 成功后才对其他 agent 可见。永远不要跳过 push。

---

## 2. 目录地图

| 路径 | 用途 | 是否需要锁 |
|---|---|---|
| `discussion/` | 公共讨论：`problem.md` 题目拆解、`ideas.md` 思路、`decisions.md` 决策 | **读→免锁**（只查 W 锁）；写→写锁 W |
| `requests/` | 每个 agent 的请求/状态板 | **不需要锁**（各自只写自己的文件） |
| `code/` | 代码 | **读→免锁**（只查 W 锁）；写→写锁 W |
| `results/` | 实验结果、图表、输出 | **读→免锁**（只查 W 锁）；写→写锁 W |
| `files/` | 原始(`raw/`)/中间(`intermediate/`)/最终(`final/`)文件 | **读→免锁**（只查 W 锁）；写→写锁 W |
| `locks/` | 锁状态文件，**只能按第 3 节协议编辑** | 由协议管理 |

> **可加锁资源**只有 4 个：`code`、`results`、`discussion`、`files`，分别对应 `locks/code.lock` 等。锁文件是**资源级文件**，每一行锁该资源下的具体文件或目录（路径级）；省略路径时表示锁整个资源目录。**只有写锁 W**（读取一律不加锁，见 3.0）。

---

## 3. 写锁协议（核心）

只有**写锁（W）**：改动某路径前必须独占它。**读取不加任何锁**（见 3.0）。底层用 **git push 的原子性**做串行化——远程仓库把所有 push 排队，两个并发抢同一路径写锁的 push 只可能一个成功，这就是锁能跨机器生效的原理。

### 3.0 为什么读取不需要锁

git 以 **commit 为原子快照**：任何人 pull 到的都是某个完整 commit 的版本，**绝不会读到“写了一半”的文件**——写方的改动是在 3.5 那一步随解锁一次性原子 push 的。因此“读锁防止读到中间态”在 git 模型下本就多余，予以废除。

读取唯一要注意的是**别读到即将过时的旧版**：若目标路径正被别人的活跃 `W` 锁盖住，说明对方正在改、新内容还没 push，你此刻 pull 到的是旧版——**先别读**，等对方释放后再 pull 最新。所以读取规则是：**查目标路径有无活跃 W 锁；有则暂缓，无则直接读**（0 锁、0 push）。

### 3.1 锁文件格式

`locks/<资源>.lock` 是纯文本：

- `#` 开头是注释，空行忽略；
- 每个**活跃写锁持有者**一行：`W <agent> <UTC时间戳> <路径>`
  - `W` = 写锁（独占其路径范围）
  - 路径：资源下的具体文件或目录，例如 `code/solver.py`、`code/models/`、`discussion/decisions.md`
- **兼容旧格式**：若一行只有 `W <agent> <UTC时间戳>`（省略路径），视为锁住整个资源目录（例如 `locks/code.lock` 中省略路径等价于 `code/`）。
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
- 一律使用仓库相对路径，用 `/` 分隔，不用 Windows 反斜杠。
- 文件路径写完整文件名，例如 `code/main.py`。
- 目录路径必须以 `/` 结尾，例如 `code/models/`；资源根目录写作 `code/`、`results/`、`discussion/`、`files/`。
- 路径必须位于对应资源目录下：`locks/code.lock` 只能写 `code/...`。

**生成 UTC 时间戳**（三台机器时区可能不同，一律用 UTC）：
- PowerShell：`(Get-Date).ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ssZ")`
- bash：`date -u +%Y-%m-%dT%H:%M:%SZ`

### 3.2 兼容规则（判断能否拿写锁）

判断一把新写锁能否拿，分两步：

1. 忽略注释行、空行、以及已过期（超租约）的行。
2. 只比较**路径重叠**的活跃写锁；路径不重叠则互不影响、可并行。

路径重叠规则：

| 已有路径 | 新路径 | 是否重叠 |
|---|---|---|
| `code/a.py` | `code/a.py` | 是 |
| `code/a.py` | `code/b.py` | 否 |
| `code/models/` | `code/models/solver.py` | 是 |
| `code/models/` | `code/plot.py` | 否 |
| `code/` | `code/任何路径` | 是 |
| 省略路径旧格式 | 该资源下任何路径 | 是 |

路径重叠后的写锁规则（只剩一种锁，规则极简）：

| 你想要的锁 | 重叠范围内有活跃 `W` | 能否拿 |
|---|---|---|
| 写锁 W | 无 | ✅ 可以（追加一行 W） |
| 写锁 W | 有 | ❌ 等待（等对方释放，或租约过期后抢占） |

> “**活跃**” = 时间戳未超过租约（见 3.6）。已过期的行按不存在处理，可在你的 acquire 提交里顺手删除并抢占。

### 3.3 拿写锁（acquire）—— 精确步骤

目标：资源 `R`（code/results/discussion/files 之一），路径 `P`（仓库相对路径，必须位于 `R` 下；锁整个资源写 `R/`）。按 1.0-B 第 2 步，锁行与「状态」合并成一个 commit：

```bash
# 1) 同步到最新锁状态
git pull --rebase

# 2) 打开 locks/R.lock，忽略注释/空行/已过期行，
#    只看与 P 路径重叠的活跃 W 行，按 3.2 判断：
#      · 有重叠的活跃 W → 等待 15~30 秒，回到步骤 1 重试（不硬闯、不改别人的行）
#      · 无             → 继续

# 3) 编辑 locks/R.lock：追加你的一行（顺手删掉已过期的行）
#      W agent_A 2026-09-09T14:30:00Z code/models/solver.py
#      锁整个资源： W agent_A 2026-09-09T14:30:00Z code/

# 4) 锁行 + 状态板 放进同一个 commit
git add locks/R.lock requests/agent_A.md
git commit -m "lock: agent_A acquire W on code/models/solver.py + status"

# 5) 推送——锁在这一刻才真正生效
git push
#   · push 成功 → 拿锁成功，可以开始写 P
#   · push 被拒（non-fast-forward，有人抢先动了锁）→ 见 3.4 回退后重试
```

### 3.4 push 被拒的回退（安全，不丢你其它工作）

拿锁的 commit 现在**同时含锁文件和状态板**（不再是“只含锁文件”），回退用 `--autostash` 兜住工作区：

```bash
git reset --soft HEAD~1                        # 撤销这次「锁+状态」提交，改动退回暂存区
git restore --staged --worktree locks/R.lock   # 只还原锁文件（丢弃你的加锁行）；状态板改动保留
git pull --rebase --autostash                  # 拉对方刚推上来的锁状态；autostash 自动兜起暂存改动再恢复
# 回到 3.3 步骤 2 重新判断（对方可能已加了与你冲突的锁），重新写锁行 → commit → push
```

> 状态板 `requests/agent_<你>.md` 是单一 owner、免锁，**永不与人冲突**；冲突只可能来自锁文件。回退只丢弃你那条加锁行，状态改动和其它未提交工作都不会丢。

### 3.5 写内容 + 释放锁（release）—— 合并成一次 push

在锁 + 租约保护下写完内容后，**把「内容 + 删锁行 + 改状态」放进同一个 commit 一次 push**（1.0-B 第 4 步）：

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

> **务必释放**（删掉自己那行并 push）。内容与解锁在同一次 push 原子生效，不存在“内容已发布但锁没放”或“锁放了但内容没发布”的中间态。用完不放锁会阻塞对应路径的协作（虽有租约兜底，但别依赖它）。

### 3.6 租约与抢占失效锁（防死锁兜底）

- 每条锁行带时间戳，**租约 30 分钟**：`现在(UTC) - 时间戳 > 30 分钟` 即视为**失效**。
- 失效的行在你拿锁时**当作不存在**，可在你的 acquire 提交里顺手删除并抢占。
- **长时间持锁要续租**：每 15~20 分钟更新一次你那行的时间戳（pull → 改时间戳 → commit → push，push 被拒走 3.4）。否则会被别人当失效抢走。
- 抢占别人的“疑似失效”写锁前，最好先在 `requests/` 里 @ 一下对方确认，避免误抢正在续租的操作。

### 3.7 同时需要多个资源或多个路径（防死锁）

- 需要同时持有多把写锁时，**一律按固定顺序申请**：`code → discussion → files → results`（字母序）。
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

- **状态优先（硬性顺序，见 1.0-B）**：写任何共享内容之前，先把「你要做什么」写进本文件「当前状态 · 正在做」，**和加锁合并成一个 commit push 出去**；做完在最后一次 push 里把状态改为进度或删回「空闲」。绝不允许先写内容、后补状态。读取不产出内容时无需报状态（0 push）。
- 每个 agent 只写自己的 `requests/agent_<你>.md`，**不需要锁**（单一 owner，天然无冲突）。
- **需要别人做事**：在**你自己的**文件里追加一行，`@` 目标 agent：
  ```
  - [2026-09-09T14:30Z] @agent_B 请把 results/fig3.png 重画成 300dpi  状态:待认领
  ```
- **发现指派给自己的请求**：定期读三个 `requests/*.md`（读请求区**不需要锁**），看到 `@你` 且"待认领"的，就在**你自己的**文件里登记认领与进度。
- **完成后回报**：也在**你自己的**文件里写一行通知发起方（例如 `@agent_A 你要的高清图已完成，见 results/fig3.png`），发起方轮询得知。**不要去改对方的文件。**

---

## 6. 讨论区规范（discussion/）

- 读讨论区：**免锁**，只查 `locks/discussion.lock` 里目标文件有无活跃 `W` 锁（有则等对方改完再读）；写讨论区：拿对应路径的写锁 W（见第 3 节）。
- **只追加，不改写他人条目**。每条署名 + UTC 时间戳：
  ```
  ## [agent_A 2026-09-09T14:30Z] 建议用元胞自动机建模车流
  理由：……
  ```
- `decisions.md` 记录**已定决策**：决策内容 + 理由 + 参与者 + 时间。定了就别反复推翻，要改需在此说明原因。

---

## 7. 禁止事项（红线）

- ❌ 写 `code/ results/ discussion/ files/` 前不查锁 / 不加写锁 W。（读取免锁，但目标被活跃 W 锁盖住时应暂缓读）
- ❌ 手动修改或删除**别人未过期**的锁行（只能删已过期的，且在你的 acquire 提交里）。
- ❌ 只 `commit` 不 `push` 就以为拿了锁 / 发布了成果。
- ❌ 写别人的 `requests/agent_X.md`。
- ❌ `git push --force` 到 `main`。
- ❌ 冒用他人 agent ID。
- ❌ 把大数据集/临时文件/编译产物提交进仓库（见 `.gitignore`）。

---

## 8. 完整示例

### 示例一：读一段代码（免锁，只查写锁）
```bash
git pull --rebase                       # 前置① 查远程
# 前置② 查 locks/code.lock：目标 code/models/solver.py 有没有被活跃 W 行盖住？
#   · 有 W 锁 → 有人正在改，先别读，等释放后再 pull 最新
#   · 无 W 锁 → 直接读，不加锁、不 push
cat code/models/solver.py               # 直接读
```
> 读取全程 **0 push、0 锁**：git commit 是原子快照，读到的永远是完整版本。

### 示例二：改代码并产出结果（写锁 + 合并 push，共 3 次网络往返）
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

---

_最后更新：2026-09-09。修改本协议前，先在 `discussion/decisions.md` 记录共识，再改本文件并通知全部 agent。_
