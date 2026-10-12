不同场景下的git使用：
> 场景1：本地 main 和远程 main 各自有新提交，发生了分叉。请把本地 main 同步并成功推送到远程，使远程 main 与本地 main 一致，且两边改动（local.txt 与 remote.txt）都保留。

/// 做法：
1. merge
```bash
git fetch origin main # 获取远程仓库的最新状态
git merge origin/main # 将远程的仓库的体提交历史合并到本地的历史中
git push origin main
```
2. rebase
```bash
git fetch origin main
git rebase origin/main
git push origin main
```

> 场景2：分支 feature 领先 main 一个提交，且 main 没有自己的新提交。请把 feature 合并进 main，要求不产生多余信息、完成后 main 指向 feature 的提交。

/// 做法：
```bash
git merge feature # 直接合并分支
```

> 第 3 题：三方合并 (生成 merge commit)
[任务]
main 和 feature 各有独立提交，已分叉。请把 feature 合并进 main，要求生成一个合并提交（merge commit），并且 main 上同时包含两边的改动。

/// 做法：
```bash
git merge feature
```

> 第 4 题：合并内容冲突：手动解决
[任务]
main 和 feature 都改了 conflict.txt 的中间一行。请把 feature 合并进 main，并把冲突解决为如下内容（三行）：
  top
  resolved
  bottom
解决后不要残留冲突标记，并完成提交。

/// 做法：
```bash
git log HEAD..origin/main --oneline # 查看origin/main中有而本地没有的提交
git log origin/main..HEAD --oneline # 查看HEAD处有的但origin/main中没有的提交
git diff origin/main # 对比两个分支的差异
# 找到冲突的位置
# 手动的解决冲突
git add conflict.txt
git commit
# 即可自动合并
```

> 第 5 题：冲突选边 (--ours / --theirs)
[任务]
合并 feature 时 conflict.txt 发生冲突。请解决冲突：整份文件采用 feature（对方）那一版的内容。

/// 做法：
```bash
# 找到冲突的文件
git checkout --their conflict.txt # 把该文件恢复成对方（feature）在冲突时的版本。
```

> 第 6 题：修改/删除冲突 (modify/delete)
[任务]
feature 删除了 docs.txt，而 main 修改了 docs.txt，合并时冲突。请解决：保留被修改后的 docs.txt（内容为 'DOCS-v2'），并完成合并。

/// 做法：
```bash
git merge feature
git add docx.txt
git commit
```

> 第 7 题：双方新增同名文件 (add/add)
[任务]
main 和 feature 各自新建了 new.txt 且内容不同，合并时 add/add 冲突。请解决为内容 'combined'，并完成合并。

/// 做法：
```bash
做法同上面的冲突处理，所有的冲突的处理都是一样的，只是对冲突内容的更改不一样而已
```

> 第 8 题：二进制文件冲突
[任务]
logo.bin 是二进制文件，main 和 feature 各改了一版，合并无法自动合并。请解决冲突：采用 feature 那一版（内容为 'LOGO-THEIRS-v2' 加两个二进制字节），并完成合并。

/// 做法：
```bash
和这个题目的做法一致：第 5 题：冲突选边 (--ours / --theirs)
```

> 第 9 题：撤销一次合并 (reset)
[任务]
main 上已经做过一次 feature 的合并（产生了合并提交）。现在想彻底撤销这次合并，把 main 恢复到合并前的状态。目标提交已用分支 premerge 标记。

/// 做法：
```bash
用 git reset --hard premerge：把 main 的指针直接退回到合并前的那个提交，合并提交被丢弃，工作区也一并还原。
```

> 第 10 题：用 revert 撤销一个合并提交
[任务]
main 上有一个把 feature 并入的合并提交，feature 新增了 feat.txt。请用 revert 撤销这个合并提交（保留历史），使 main 上不再包含 feat.txt。

/// 做法：
```bash
git revert -m 1 34c2e699152f89419407a59a9e05dfaea014b630
git revert -m 1 <merge提交> 的作用是：以合并提交的第 1 个父提交（主线 main）为基准，计算这次合并引入的改动，然后把它们“反向施加”，生成一个新提交来抵消这次合并。
```

> 第 11 题：pull --rebase 避免产生 merge commit
[任务]
本地 main 与远程 main 分叉。请在不产生合并提交（历史保持一条直线）的前提下同步远程改动，并成功推送，使远程与本地一致。

/// 做法：
```bash
git pull --rebase 同步分叉，避免产生 merge commit 的题。本质就是前面“场景1”的 rebase 做法，只是把 fetch + rebase 合成一条命令。
它是什么
git pull --rebase origin main
   =   git fetch origin main      # 下载远程最新
   +   git rebase origin/main     # 把本地提交“重放”到远程最新之上
普通 git pull = fetch + merge → 会产生合并提交，历史分叉。
git pull --rebase = fetch + rebase → 把你在本地的提交接到远程提交后面，历史一条直线，无合并提交。
```

> 第 14 题：rebase -i 压缩提交 (squash)
[任务]
feature 上有 3 个提交。请把它们压缩成 1 个提交（内容不变），使 feature 相对 base 只多出一个提交。

/// 做法：
```bash
# 1. 切到 feature，以 base 为基点交互式变基
git checkout feature
git rebase -i base          # 等价于 git rebase -i HEAD~3

# 2. 编辑提交列表：第一条保持 pick，后两条改 squash
pick   C1
squash C2
squash C3

# 3. 弹出“合并提交信息”编辑器：删掉 # 注释行和多条信息，只留一行，保存退出
```
































































/// little
> push推送的东西：
> 1. 只推当前分支（默认）→ 要推所有分支用 git push > --all，推标签用 --tags。
> 2. 只推远程没有的 → 远程已有的不重传。
> 3. 必须是"可达"的提交 → 只有从被推分支顺着父指针能走到> 的才算。
> 4. 未 commit 的改动不推 → 工作区/暂存区内容不会上去。
> 5. 要能快进 → 如果远程有你没有的提交，push 会被拒（需> 先 pull）。


> git diff 的输出是统一 diff 格式，看这几个关键部分：
> diff --git a/src/main.c b/src/main.c     ← 文件标识（a/=旧，b/=新）
> index 3f2e1a0..9c4b7d2 100644            ← 旧/新 blob 哈希
> --- a/src/main.c                         ← 旧版本（-）
> +++ b/src/main.c                         ← 新版本（+）
> @@ -10,7 +10,8 @@ void foo() {           ← 区块头：旧从第10行起7行，新从第10行起8行
>      int x = 1;                           ← 前面空格 = 没变
> -    int y = 2;                           ← 减号 = 旧版有、新版删了
> +    int y = 3;                           ← 加号 = 新版新增/改成这行
> +    int z = 4;
>      return x;                            ← 空格 = 上下文，未变
> 核心规则：
> - - 开头：你（工作区）相比 origin/main 删掉的（旧有的行）
> - + 开头：你（工作区）相比 origin/main 新加的（现有的行）
> - 空格开头：两边都有的上下文行
> - @@ -旧起始,行数 +新起始,行数 @@：定位改动位置
> - diff --git a/x b/x：每个文件一段，文件本身新增/删除时还会有 new file mode / deleted file mode
> 所以整体读法：*- 是远程分支的旧内容，+ 是你本地现在的样子*。改动越多、文件越多，说明你本地偏离远程越多。
>
> diff --git a/src/main.c b/src/main.c
> - 每个被改动文件的开头。
> - diff --git 是固定开头。
> - a/src/main.c 是旧文件路径，b/src/main.c 是新文件路径。
> - a/、b/ 是 Git 加的前缀，占位用（避免路径歧义），不是真实目录。
> index 3f2e1a0..9c4b7d2 100644
> - 3f2e1a0：旧版本的 blob（文件内容对象）短哈希。
> - 9c4b7d2：新版本的 blob 短哈希。
> - 100644：文件权限模式（普通文件，非可执行；可执行是 100755，符号链接是 120000）。
> --- a/src/main.c
> - 三个 -，表示旧文件（左边）。
> - 路径就是上面的 a/src/main.c。
> - 文件被删除时会变成 --- /dev/null。
> +++ b/src/main.c
> - 三个 +，表示新文件（右边）。
> - 路径是 b/src/main.c。
> - 文件是新增时，旧侧会是 --- /dev/null，新侧是正常路径。
> @@ -10,7 +10,8 @@ void foo() {
> - 区块头（hunk header），表示下面这一块改动的位置。
> - -10,7：在旧文件里，从第 10 行开始，涵盖 7 行。
> - +10,8：在新文件里，从第 10 行开始，涵盖 8 行。
> - （7→8，因为净新增了 1 行。）
> - void foo() { 是紧挨着这块改动的最近的函数/上下文提示，帮你知道改的是哪个函数，不是内容本身。
>      int x = 1;
> - 行首是空格，表示这行两边都有、没变，只是拿来当上下文。
> - 这里 int x = 1; 在旧、新文件里都存在。
> -    int y = 2;
> - 行首 -，表示这行是旧文件里有、但被删除/替换掉了。
> - 内容 int y = 2; 是旧版本的样子。
> +    int y = 3;
> - 行首 +，表示这行是新文件里新增的。
> - 内容 int y = 3; 是新版本的样子。
> - 和上一行合起来看：原来 y = 2，现在改成了 y = 3（一删一加）。
> +    int z = 4;
> - 又一行新增，新版本里多出来的。
>      return x;
> - 又是空格开头，没变的上下文行。




> merge和rebase
> git merge origin/main
> 把两条线汇合，额外生成一个合并提交 M（有两个父）：
> base ──● local change ──┐
>       └─● remote change ─┴─● M   ← 合并提交
> - 保留“曾经分叉过”的真实历史
> - 你本地的提交 local change 哈希不变
> - 多一个合并提交，历史是“有分叉的树”
> - 可能有冲突（本题没有）
> git rebase origin/main
> 把你本地的提交摘下来、接到远程后面，历史拉成一条直线：
> base ──● remote change ──● local change'   ← 你的提交被重放了（新哈希）
> - 历史是一条干净的直线，没有合并提交
> - 你本地的提交被改写（内容一样，但父提交变了 → 哈希变了，带 '）
> - 也可能有冲突，且是逐个提交处理

> 快速合并（fast-forward） 是 merge 的一种特殊情况：当目标分支（如 main）没有自己的新提交，只是落后于被合并分支时，Git 不产生合并提交，直接把分支指针向前滑动到对方的最新提交。 

> 三方合并（three-way merge）
> 当两条分支分叉了（各自都有新提交，无法 fast-forward），Git 需要合并它们。它会找三个东西：
> - base（共同祖先）：两条分支分叉前的那个公共提交（merge base）
> - ours（我们）：当前分支（如 main）的最新提交
> - theirs（他们）：要合并进来的分支（如 origin/main）的最新提交
> 然后逐文件、逐行比较：
>         A---B  (theirs, origin/main)
>        /
>   ...X  ← base（共同祖先）
>        \
>         C---D  (ours, main)  ← HEAD
> - 如果某行 ours 改了、theirs 没改 → 取 ours
> - 如果某行 theirs 改了、ours 没改 → 取 theirs
> - 如果某行 两边都改了且改法不同 → 冲突（conflict），需要你手动解决
> - 两边都没改 → 保持原样
> 因为是用三个点（base/ours/theirs）而不是两个来判断改动，所以叫三方合并。这也叫“3-way merge”。（对比：fast-forward 是 2 个点的直接滑动，不需要 base。）
> 合并提交（merge commit）
> 三方合并成功后会自动生成一个新提交，它最大的特点是有两个父提交：
>   D---E---A---B   (their)
>        \       \
>         C---F---M  main   ← M 就是合并提交
> - M 的父是 F（ours）和 B（theirs），即 git log 里看到 Merge: 两个哈希那行。
> - 提交信息默认是 Merge branch 'xxx' into yyy。
> - 它的工作区内容 = 合并后的结果（两边改动都在）。
> 一句话总结：分叉时用 base/ours/theirs 三点合并内容，合并成功后生成的、有两个父亲的提交就是合并提交。 

> 规律：只要需要“三方合并”（有共同 base + 两份不同改动），且改到同一区域，就会冲突。
> 冲突只在真正执行整合命令的那一刻才暴露
> merge 冲突时 Git 会进入“合并中”状态（记录了 MERGE_HEAD 等）。之后你 git commit，Git 检测到这个状态，就自动把它做成有> 两个父提交的合并提交，并复用默认的合并信息（Merge branch 'feature' into main）。
> 必须先把所有冲突文件都 git add。只要还有未解决（Unmerged paths）的文件，git commit 会拒绝

> git merge feature 时，conflict.txt 两边都改了、冲突了。题目要求不要一点点手动挑，而是把整个文件直接换成 feature 分支> 的版本（即对方版本），然后完成合并。
> 这里的方向很关键：
> 你在 main 上执行 git merge feature
> ours（我方）= 当前分支 main
> theirs（对方）= 被合并进来的 feature
> 所以要“采用 feature 那一版”就是取 theirs：
> git checkout main
> git merge feature
> \# CONFLICT in conflict.txt
> 
> git checkout --theirs conflict.txt   # 整份文件用 feature 版本覆盖
> git add conflict.txt
> git commit                            # 完成合并提交
> 说明：
> git checkout --theirs <file>：把该文件恢复成对方（feature）在冲突时的版本。
> git checkout --ours <file>：则取我方（main）版本。
> “整份文件采用某一版”只需要这一条命令，不用手动删冲突标记——--ours/--theirs 拿到的就是干净的、无冲突标记的版本。
> 之后同样要 git add + git commit 才真正完成合并。
> 注意：rebase 时 ours/theirs 会反过来（rebase 中 ours = 被变基到的基底，theirs = 你正在重放的提交），这也是这类题常考的坑。这里明确是 merge，所以 theirs = feature。

> 若工作区被删了，用 git checkout main -- docs.txt 取回” 前提是工作区里的 docs.txt 不见了（比如你手滑删了、或某些工具把它清掉了）。

> 三方合并能自动合并，是因为能对比 base→ours 和 base→theirs 的差异。
> - base 存在且两边改的是不同行 → 能自动合并。
> - base 不存在 → 没有可供对比的旧版本，两边都是“凭空新增且内容不同”，Git 没有任何依据去挑或合，只能判定为冲突，交给你。 

> git revert -m 1 <merge提交> 的作用是：以合并提交的第 1 个父提交（主线 main）为基准，计算这次合并引入的改动，然后把它> 们“反向施加”，生成一个新提交来抵消这次合并。
> 为什么必须带 -m
> 普通提交只有一个父，revert 就“拿它和父的差异取反”。但合并提交有两个父，Git 不知道拿哪个当基准，所以必须用 -m 指明主线：
>         P1 (父1 = main，合并前的主线)
>        /  \
>       /    M  ← 合并提交 main
>       \  /
>         P2 (父2 = feature)
> - -m 1 → 基准 = P1（main）
> - -m 2 → 基准 = P2（feature）
> 具体发生的变化
> 1. 算出要撤销的改动：diff(P1 → M) 就是这次合并“净带来”的东西（feature 的内容，比如新增 feat.txt）。
> 2. 取反生成新提交：在 M 之后新建一个提交 R，内容 = 把上面那些改动反过来：
> - feature 新增的文件 → 删除（feat.txt 没了）
> - feature 改过的行 → 还原
> - feature 删过的 → 恢复
> 3. 历史保留：合并提交 M 依然存在，只是在它后面多了一个 R。
>   P1 --- M --- R   main     （R 抵消了 M 引入的 feature 改动）
>    \   /
>     P2
> 工作区/暂存区：执行后会自动应用并提交 R（默认直接 commit；加 -n 则只改暂存区不提交）。
> 和你前面 merge 的对应关系
> - merge 把 feature 的改动“加进来”。
> - revert -m 1 正好把它们“减回去”，所以 main 上不再有 feat.txt。 

> git rebase --continue 是 rebase 卡住（通常是冲突或 edit 停下）之后，告诉 Git“这个提交我处理好了，继续往下变基” 的命令。
> 其实 merge 也有 git merge --continue（Git 2.12+ 才有），只是可省略，而 rebase 的 --continue 基本是必须的。 