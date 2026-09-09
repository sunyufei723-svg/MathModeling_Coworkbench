# 数模国赛 · 三人 × Agent 共享工作区

一个用 **git 仓库**搭建的协作工作区：3 名队员各用一个 agent（1 个 Qoder + 2 个 codex），
在各自电脑上通过远程仓库协同完成数学建模国赛。核心是一套**严格读写锁**协议，保证多个
agent 并发读写共享文件时不互相覆盖，并支持同一资源内按具体路径并行加锁。

- **人看的规范**：本文件（`README.md`）。
- **agent 入口**：[`AGENTS.md`](AGENTS.md)（codex 自动读取，仅摘要 + 导向 rules.md）。
- **agent 完整规则**：[`rules.md`](rules.md)（权威协议，最高优先级；冲突一律以 `rules.md` 为准）。

---

## 快速上手

```bash
# 1) 克隆仓库（远程地址由队长提供）
git clone <远程仓库地址> modeling
cd modeling

# 2) 认领你的 agent 身份：agent_A / agent_B / agent_C（三人各一个，全程不变）
#    在你的 requests/agent_<你>.md 顶部写上你负责的方向

# 3) 每次开工先同步
git pull --rebase
```

> 队长首次配置远程仓库见文末「仓库初始化」。

---

## 目录结构

```
.
├── README.md          # 本文件：团队总体工作规范（人看）
├── AGENTS.md          # 入口：codex 自动读取，导向 rules.md
├── rules.md           # Agent 完整协作规则（权威协议）
├── .gitignore         # 忽略大数据/临时/编译产物
├── .gitattributes     # 统一换行符、锁文件处理策略
│
├── discussion/        # 公共讨论区（共享，读/写需锁）
│   ├── problem.md     #   题目理解与拆解
│   ├── ideas.md       #   思路/方法（只追加）
│   └── decisions.md   #   已定决策与理由（只追加）
│
├── requests/          # 请求区（每人只写自己的，无需锁）
│   ├── agent_A.md
│   ├── agent_B.md
│   └── agent_C.md
│
├── code/              # 代码（共享，读/写需锁）
├── results/           # 实验结果、图表、输出（共享，读/写需锁）
├── files/             # 文件（共享，读/写需锁）
│   ├── raw/           #   原始数据（只读为主）
│   ├── intermediate/  #   中间产物
│   └── final/         #   最终交付
│
└── locks/             # 锁状态文件（只能按协议编辑，勿手改）
    ├── code.lock
    ├── results.lock
    ├── discussion.lock
    └── files.lock
```

---

## 协作总原则

1. **各自电脑 + 远程仓库同步**：一切以远程 `main` 为准，勤 `pull --rebase`、勤 `push`。
2. **共享资源先加锁再动手**：`code/ results/ discussion/ files/` 是共享区，读要读锁、写要写锁；优先锁具体文件或目录，必要时才锁整个资源。
3. **请求区单一 owner**：`requests/agent_X.md` 只有 X 本人写，别人只读——所以请求区**不用加锁**。
4. **讨论只追加、不改别人**：`ideas.md` / `decisions.md` 每条署名 + 时间戳，追加而非重写。
5. **成果及时推送**：本地 commit 只有 push 后别人才能看到。

---

## 读写锁规则（核心，务必理解）

采用**严格读写锁**语义：

- **读锁 R**：多个 agent 可同时持有（读读兼容）。
- **写锁 W**：独占，持有期间**不允许任何其他锁**（读写、写写都互斥）。
- 规则一句话：**读共享文件前拿读锁，改共享文件前拿写锁。**

### 为什么这样能在多台电脑上生效

git 没有跨网络的"原子加锁"，但 **`git push` 是原子的**——远程仓库会把所有 push 排队，
非快进的 push 会被拒绝。于是：两个人同时抢同一把写锁，只有一个能 push 成功，另一个被拒后
重新拉取、发现锁已被占，就退让。**push 成功 = 拿锁成功**，这就是锁跨机器生效的原理。

### 锁文件长什么样

`locks/code.lock` 里，`#` 是注释，每个持有者一行 `模式 agent 时间戳(UTC) 路径`；空文件 = 没加锁：

```
# 锁文件：code
W agent_A 2026-09-09T14:30:00Z code/models/solver.py
W agent_B 2026-09-09T14:31:10Z code/plotting/charts.py
```
```
# 锁文件：discussion
R agent_A 2026-09-09T14:30:00Z discussion/ideas.md
R agent_B 2026-09-09T14:31:10Z discussion/ideas.md
```

省略路径的旧格式仍有效，视为锁住整个资源目录。

### 拿锁 / 放锁的完整步骤（精确 git 命令）

见 [`rules.md` 第 3 节](rules.md)，那里是给 agent 的权威版本。人肉速记：

```
拿锁： git pull --rebase
       → 看 locks/R.lock 是否兼容（只比较路径重叠的活跃锁）
       → 兼容就加自己一行，格式为 模式 agent 时间戳 路径 → git add locks/R.lock → git commit → git push
       → push 成功=拿到；push 被拒=有人抢先，软回退后重试：
         git reset --soft HEAD~1 ; git restore --staged --worktree locks/R.lock ; git pull --rebase
放锁： 先把成果 commit + push（仍在持锁期间）
       → git pull --rebase → 删掉自己那行 → git add → commit → push
```

### 防死锁：租约 30 分钟

- 每个锁行带 UTC 时间戳，**超过 30 分钟没更新 = 失效**，别人可当它不存在并抢占。
- 这样即使某个 agent 崩溃没放锁，也不会把全队卡死。
- **长时间持锁要续租**：每 15~20 分钟更新一次自己那行的时间戳。
- 同时需要多把锁时，**按固定顺序申请**：`code → discussion → files → results`；同一资源内多个路径按目录优先、路径字母序申请，避免交叉等待。

---

## git 工作流

- 单 `main` 分支协作；开工前、push 前都 `git pull --rebase`。
- 提交信息前缀：`lock:` / `code:` / `results:` / `files:` / `discussion:` / `req:` / `docs:` / `wip:`。
- **禁止** `git push --force` 到 `main`。
- 锁文件冲突不要手工硬拼：`git rebase --abort` → 重新 `pull --rebase` → 重走拿锁流程。

---

## 请求机制（怎么让别的 agent 帮你做事）

- 在**你自己的** `requests/agent_<你>.md` 里追加一行，`@` 目标：
  `- [时间] @agent_B 请把 results/fig3.png 重画成 300dpi  状态:待认领`
- 别人定期读三个请求文件，看到 `@自己` 的就在**他自己的**文件里认领、更新进度、完成后回报。
- 全程**只写自己的请求文件**，不改别人的——因此请求区无需加锁、也无冲突。

---

## 仓库初始化（队长首次操作）

```bash
# 在 GitHub / Gitee 建一个空仓库（不要勾选自动生成 README），拿到地址后：
git remote add origin <远程仓库地址>
git add -A
git commit -m "init: 数模共享工作区骨架 + 读写锁协作协议"
git push -u origin main
```

其余两名队员 `git clone` 后即可开工。建议：

- **平台**：国内访问 Gitee 更稳；GitHub 亦可。任选其一，三人统一。
- **大数据**：`files/raw/` 里若有很大的数据集，考虑用 Git LFS，或约定只入库小样本、大数据另传网盘（在 `decisions.md` 记录）。

---

_本工作区由三人共同维护。修改协作规范前，先在 `discussion/decisions.md` 记录共识。_

