# Git 合并（Merge）与冲突（Conflict）详解笔记

> 配套笔记：`git-push-笔记.md`（push / commit / 父提交 / PR）

---

# 第一部分：Git 合并（Merge）详解

## 1. 什么是合并

合并 = 把**一个分支的改动融合进另一个分支**。它做的事是：找到两个分支的**共同祖先**，把两边自祖先以来的改动整合成一个统一结果。

```bash
git checkout main      # 站在目标分支（要并入的分支）
git merge feature      # 把 feature 合进 main
```

方向说明：`git merge feature` 的意思是"把 feature 合进**当前所在分支**"，当前分支是接收方。

## 2. 底层原理：三方合并

Git 合并靠**三个版本**对比：

```
        共同祖先 (base)
        /            \
   main 最新        feature 最新
```

- **base**：两分支的分叉点
- **ours**：当前分支（main）的最新
- **theirs**：要合入的分支（feature）的最新

Git 逐行对比 base→ours 和 base→theirs 的差异，把不同改动叠加。两边改了不同地方 → 自动合并；改了同一地方 → 冲突。

## 3. 三种合并结果

### (1) 快进合并 Fast-forward

条件：**当前分支没有新提交**，只是落后于目标分支。也就是两个分支**没有分叉**，是直线关系。

用时间线理解：

第 1 步，从 main 建分支：

```
A ← B          ← main 和 feature 都指向 B
     \
      (feature 也指向 B)
```

第 2 步，在 feature 上提交两次，main 没动：

```
A ← B ← C ← D      ← feature 在这里
    ↑
  main 还在这里
```

第 3 步，切到 main 然后合并：

```bash
git checkout main
git merge feature
```

Git 一看：main 没有任何 feature 不知道的提交，两边是直线关系。于是**不动任何文件内容**，只把 main 指针从 B 直接移到 D：

```
A ← B ← C ← D      ← main 和 feature 都指向 D
```

**没有产生新 commit！**

为什么叫"快进"：指针从 B "跳"到 D，中间不产生分叉节点，像按了快进键。

另一条命令 `git merge --no-ff feature` 会强制生成合并 commit，保留分支痕迹：

```
A ← B ←───── M      ← 明确看到 feature 从 B 分出去又并回来
       \     /
        C ← D
```

### (2) 三方合并 Three-way merge

条件：**两个分支各有新提交**，发生了分叉。

"三方"指对比时用的三个版本：

| 方 | 名称 | 含义 |
|----|------|------|
| base | 共同祖先 | 两分支分叉前最后一个共同提交 |
| ours | 当前分支 | 你站着的那条分支（main）的最新 |
| theirs | 对方分支 | 要合入的分支（feature）的最新 |

用时间线理解：

第 1 步，从 main 建 feature 分支：

```
A ← B          ← main 和 feature 都在 B
```

第 2 步，两边各自提交（关键：分叉了）：

```
        C          ← main 提交了 C
       /
A ← B
       \
        D          ← feature 提交了 D
```

第 3 步，合并：

```bash
git checkout main
git merge feature
```

Git 发现两边都动了，**不能快进**，于是：

1. 找到 base = B
2. 把 C 和 D 的改动都叠加
3. 生成一个**新的合并 commit M**

```
        C
       / \
A ← B     M        ← M 是新的合并 commit
       \ /
        D
```

M 的**文件内容** = B 的基础上，同时应用了 C 的改动 **和** D 的改动。

M 的**父提交** = 同时指向 C 和 D（它"承认"自己是从这两条线来的）。

```bash
git cat-file -p M
# parent C
# parent D      ← 两个父
```

注意区分：
- **内容上**：M 包含了 C 和 D 的合并结果。
- **历史上**：C 和 D 这两个 commit 本身并没有被"塞进"M 里，它们是 M 的两个父，M 是它们之上的一个新节点。

三方合并的三种情况：

```
# (1) 改的地方不同 → 自动合并
base:    hello
ours:    hello world        (改了后面)
theirs:  Hi hello           (改了前面)
结果:    Hi hello world      (叠加，无冲突)

# (2) 只有一边改了某处 → 直接采用
base:    x = 1
ours:    x = 1              (没改)
theirs:  x = 2              (改了)
结果:    x = 2

# (3) 两边改了同一处 → 冲突
base:    x = 1
ours:    x = 2
theirs:  x = 3
→ Git 无法决定，标记冲突，需人工处理
```

### 快进 vs 三方合并对比

| | 快进 Fast-forward | 三方合并 Three-way |
|---|---|---|
| 前提 | 无分叉，一方落后 | 有分叉，两边都动了 |
| 用的版本 | 直接前移指针 | base / ours / theirs |
| 是否生成新 commit | 否 | **是（合并 commit）** |
| 父提交数量 | — | **2 个** |
| 历史形状 | 一条直线 | 有分叉 + 合并节点 |
| 丢失信息 | 看不出曾有分支 | 保留分支结构 |

## 4. 常用命令与参数

| 命令 | 作用 |
|------|------|
| `git merge <分支>` | 合并指定分支进当前分支 |
| `git merge --no-ff <分支>` | 强制生成合并 commit（即使能快进） |
| `git merge --ff-only <分支>` | 只允许快进，否则报错（保证历史线性） |
| `git merge --squash <分支>` | 把对方所有改动压成一次暂存改动，不自动提交 |
| `git merge --abort` | 放弃合并，回到合并前 |
| `git merge --continue` | 解决冲突后继续合并 |
| `git merge --no-commit` | 先合并但不自动提交，方便检查 |

## 5. merge vs rebase

| | merge | rebase |
|---|---|---|
| 历史形状 | 保留分叉，有合并节点 | 一条直线 |
| 是否产生新 commit | 会产生合并 commit | 改写原 commit，不新增 |
| 是否改写历史 | 不改 | 会改写（危险，勿对公共分支用） |
| 优点 | 真实、安全 | 整洁、线性 |
| 缺点 | 历史较乱 | 改写历史、冲突逐个解决 |

原则：**已推送到远程的公共分支不要 rebase；个人本地分支可以用 rebase 整理。**

---

# 第二部分：冲突（Conflict）详解

## 6. 什么是冲突

**当两个分支对同一文件的同一处做了不同修改时，Git 无法判断该保留哪个，于是停下来让你人工决定。**

冲突不是错误，是 Git 在说："这里你们俩各说各话，我替你定不了。"

冲突的本质是"Git 无法自动决定最终结果"，**不是仅限于"同一行被改了"**。

## 7. 冲突的种类

| 大类 | 例子 | 报错关键字 |
|------|------|-----------|
| 文本内容 | 同行不同改 | `CONFLICT (content)` |
| 修改/删除 | 一边改文件，一边删文件 | `CONFLICT (modify/delete)` |
| 双方新增同名文件 | 两边各自新建同名文件且内容不同 | `CONFLICT (add/add)` |
| 重命名 | rename/rename、rename/delete、rename/modify | `CONFLICT (rename/*)` |
| 文件/目录 | 一边是文件 `foo`，一边是目录 `foo` | `CONFLICT (file/directory)` |
| 二进制 | 图片、压缩包等无法逐行合并 | `Cannot merge binary files` |
| 子模块 | 引用了子模块不同 commit | `CONFLICT (submodule)` |
| 换行符/空白 | CRLF/LF、空白差异被判为不同修改 | — |
| 环境因素 | 本地未提交/未跟踪文件会被覆盖 | `would be overwritten by merge` |

说明：

- **内容冲突**最常见：两边改了同一文件的同一处。
- **修改/删除冲突**：
  ```
  CONFLICT (modify/delete): file.txt deleted in feature
  and modified in HEAD
  ```
  你要决定：保留修改后的文件，还是接受删除。
- **add/add**：两个分支各自新建同名文件，内容还不一样。
- **重命名冲突**：rename/rename（改成不同名字）、rename/delete（一改名一删除）、rename/modify（一改名一改内容）。
- **文件/目录冲突**：路径同名但类型不同（文件 vs 目录）。
- **二进制冲突**：无法逐行合并，只能整份选一边。
- **子模块冲突**：两仓库引用子模块不同 commit。
- **换行符/空白冲突**：配置了 `text`/`eol` 属性时触发。
- **pull/checkout 时**：合并本身没冲突，但为避免覆盖本地改动而拒绝操作：
  ```
  error: Your local changes to the following files would be overwritten by merge
  ```

## 8. 冲突长什么样

冲突文件里会被插入标记：

```
<<<<<<< HEAD
x = 2                    ← 当前分支(ours/main)的版本
=======
x = 3                    ← 要合入的分支(theirs/feature)的版本
>>>>>>> feature
```

- `<<<<<<< HEAD` 到 `=======`：你当前分支的写法
- `=======` 到 `>>>>>>> feature`：对方分支的写法
- 这整段连同标记，需要你手动清理

## 9. 解决冲突的方法

### 方法一：标准手动流程（最通用）

```bash
git status                     # 1. 看哪些文件冲突（both modified）
git diff                       # 2. 看冲突具体内容
# 3. 打开文件，删掉 <<<<<<< ======= >>>>>>> 标记，留下最终内容
git add <文件>                 # 4. 标记该文件已解决
git commit                     # 5. 全部解决后提交，完成合并
```

关键点：**必须解决所有冲突文件并 `git add`，`git commit` 才会成功。**

编辑冲突时的几种选择：

```
# 选择 1: 只保留自己的
x = 2

# 选择 2: 只保留对方的
x = 3

# 选择 3: 两个都要（按需合并）
x = 2
x = 3
```

### 方法二：快速选边（不想手动编辑时）

```bash
git checkout --ours   <文件>   # 冲突处直接用当前分支(HEAD)的版本
git checkout --theirs <文件>   # 冲突处直接用对方分支的版本
git add <文件>
git commit
```

> 注意：这会**整份文件**选一边，可能丢掉另一边在该文件其他地方的**已成功自动合并**的改动。

### 方法三：可视化工具

```bash
git mergetool                  # 调用配置的对比工具（vimdiff/vscode 等）
git config --global merge.tool vscode   # 配置默认工具
```

编辑器里通常有三栏：base / ours / theirs，点一下选保留哪块，比手改标记更省心。

### 方法四：编辑器插件

- VS Code：冲突处有 "Accept Current / Accept Incoming / Accept Both" 按钮
- IDEA / JetBrains：三栏合并界面

本质上也是帮你生成正确内容，然后你仍需 `git add`。

### 方法五：放弃 / 重来

```bash
git merge --abort              # 放弃本次合并，回到合并前状态
git rebase --abort             # rebase 冲突时放弃
git cherry-pick --abort        # cherry-pick 冲突时放弃
```

已解决的单个文件想重来：

```bash
git checkout --merge <文件>    # 恢复该文件的冲突标记状态
```

### 方法六：二进制文件冲突

无法逐行合并，只能整份选一边：

```bash
git checkout --ours   model.bin
git checkout --theirs model.bin
git add model.bin
git commit
```

或提前用 `.gitattributes` 指定策略：

```
*.bin merge=binary
```

### 方法七：pull 冲突的处理

```bash
git pull                    # = fetch + merge，可能冲突
# 解决方式同上（编辑 → add → commit）

# 若想用 rebase 方式拉（历史线性）：
git pull --rebase
# rebase 冲突：解决后 git add → git rebase --continue
```

有时 `git push` 被拒：

```
! [rejected] main -> main (fetch first)
```

这通常是因为远程有你本地没有的提交，需要先 `git pull`。

## 10. 相关命令速查

```bash
git status             # 看冲突文件列表（both modified = 未解决）
git diff               # 看冲突具体内容
git mergetool          # 调出可视化工具解决冲突
git checkout --ours <文件>    # 冲突处直接采用当前分支版本
git checkout --theirs <文件>  # 冲突处直接采用对方分支版本
git checkout --merge <文件>   # 恢复该文件的冲突标记状态
git add <文件>         # 标记冲突已解决
git commit             # 完成合并
git merge --abort      # 后悔了，放弃合并回到合并前
git rebase --abort     # rebase 冲突时放弃
git cherry-pick --abort
```

多文件冲突时：

- 必须**全部** `git add` 后才能 `git commit`
- `git status` 里 `both modified` 是未解决的，`modified` 是已解决待提交的
- 只要还有未标记的冲突文件，`git commit` 会拒绝

## 11. 减少 / 预判冲突的手段

| 手段 | 说明 |
|------|------|
| 勤 `git pull` / `git fetch` | 尽早同步，减少大分叉 |
| 小步提交 | 改动块越小越易合并 |
| 分支粒度小 | 一个分支只做一件事 |
| 团队约定格式化 | 避免空白/换行符噪音冲突 |
| `git merge --no-commit` | 先合并但不自动提交，方便检查 |

## 12. 冲突处理决策表

| 情况 | 推荐做法 |
|------|---------|
| 同一处两边都有用 | 手动合并，两块都留 |
| 一边明显过时/错误 | `checkout --ours/--theirs` 选对 |
| 二进制文件 | `checkout` 选一边 |
| 改/删冲突 | 决定保留修改还是删除 |
| 太多太乱 | `git merge --abort` 重来，或换 rebase/分批合 |
| 编辑器能手点 | `git mergetool` |

## 13. 记忆口诀

> **看（status/diff）→ 改（编辑或选边）→ 标（git add）→ 提（git commit）**；搞不定就 **abort** 重来。

---

# 一句话总览

- **合并** = 以共同祖先为基准，把两个分支的改动整合到一起。没分叉则快进（只挪指针），分叉则生成带 **2 个父提交**的合并 commit，同一处冲突则手动解决后提交。
- **冲突** = Git 无法自动决定最终结果时的停顿，类型不限于同行内容冲突。解决步骤：编辑 → `git add` → `git commit`；反悔用 `git merge --abort`。