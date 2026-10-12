# 一、先理解 rebase：它究竟做了什么？

假设你的项目有两个分支：

* `main`：主分支，其他人已经提交了新代码。

* `feature`：你正在开发的功能分支。

最开始，两者有一个共同的提交 `A`。

### 变基前：两个分支各自前进

main

主分支新增了两个提交

A

B

C

main → C

feature

你的功能分支新增了两个提交

A

D

E

feature → E

A 是共同祖先；B、C 属于 main；D、E 属于 feature。

现在执行：

Bash

```
git switch feature
git rebase main
```

Git 会做的事情是：

1. 找出 `feature` 与 `main` 的共同祖先 `A`。

2. 找出 `feature` 相对于 `A` 的独有提交，也就是 `D`、`E`。

3. 先让当前分支基于 `main` 最新的提交 `C`。

4. 将 `D`、`E` 的更改依次重新应用，形成新的提交 `D'`、`E'`。

### 变基后：提交历史变成线性

### A

### B

### C

### D′

### E′

main → C

feature → E′

D′、E′ 是新提交，通常具有新的 commit SHA，但保留原提交所表达的代码更改。

注意一个非常关键的点：rebase 不是简单地把分支指针挪一下，而是重新创建提交。

所以，原来的 `D`、`E` 和新的 `D'`、`E'` 通常不是同一个提交对象。提交内容可以相同，但父提交不同，因此 SHA 也会变化。

## 1.1 rebase 和 merge 的区别

| 对比     | `git rebase main` | `git merge main` |
| ------ | ----------------- | ---------------- |
| 核心操作   | 重新应用当前分支的提交       | 合并两个分支的历史        |
| 提交 SHA | 被重放的提交通常改变        | 原有提交通常保留         |
| 历史形态   | 通常更线性             | 可能出现分叉与合并提交      |
| 解决冲突   | 可能逐个提交解决          | 通常针对整个合并过程解决     |
| 常见用途   | 整理个人开发分支          | 合并功能分支、保留分支历史    |

两者并不是谁绝对更好。个人开发分支经常使用 rebase 整理历史；团队协作中，merge 也很常见。

# 二、搭建一个可以亲手操作的 Git 实验

建议直接在终端里执行下面的命令。我们创建一个完全独立的测试仓库，不会影响你现有的项目。

## 2.1 创建实验仓库

Bash

```
mkdir git-rebase-demo
cd git-rebase-demo

git init -b main
git config user.name "Demo User"
git config user.email "demo@example.com"
```

创建第一个提交 `A`：

Bash

```
echo "version 1" > app.txt
git add app.txt
git commit -m "A: initial version"
```

然后在 `main` 上继续提交 `B`：

Bash

```
echo "main feature B" >> app.txt
git add app.txt
git commit -m "B: add main feature"
```

再创建提交 `C`：

Bash

```
echo "main feature C" >> app.txt
git add app.txt
git commit -m "C: add another main feature"
```

现在，主分支的历史是：

```
A ── B ── C    main
```

创建功能分支。为了模拟真实开发，我们从 `A` 开始开发功能：

Bash

```
git switch -c feature HEAD~2
```

因为当前位于 `C`，所以 `HEAD~2` 指向 `A`。

创建提交 `D`：

Bash

```
echo "feature D" >> app.txt
git add app.txt
git commit -m "D: add feature D"
```

创建提交 `E`：

Bash

```
echo "feature E" >> app.txt
git add app.txt
git commit -m "E: add feature E"
```

此时历史是：

```
          B ── C            main
         /
A ──────
 \
  D ── E                   feature
```

可以用下面的命令查看真实提交图：

Bash

```
git log --oneline --graph --decorate --all
```

这里几个参数分别表示：

* `--oneline`：每个提交显示为一行。

* `--graph`：用 ASCII 图显示分支结构。

* `--decorate`：显示 `main`、`feature` 等分支指针。

* `--all`：查看所有分支的提交。

## 2.2 执行第一次 rebase

确认当前位于 `feature`：

Bash

```
git switch feature
git rebase main
```

再查看历史：

Bash

```
git log --oneline --graph --decorate --all
```

理想情况下，你会看到类似这样的结构：

```
* E' (HEAD -> feature) E: add feature E
* D' D: add feature D
* C (main) C: add another main feature
* B B: add main feature
* A A: initial version
```

实际 SHA 会是你本地生成的值，不会与示意图一致。

此时：

* `main` 仍指向 `C`。

* `feature` 指向新的 `E'`。

* `D'`、`E'` 是 Git 重新创建的提交。

* 原来的 `D`、`E` 不再属于当前 `feature` 的最新历史链。

这里还有个容易忽略的细节：`git rebase main` 中的 `main` 是目标基底，而不是你要切换过去的分支。执行时当前分支仍然是 `feature`。

# 三、交互式变基：`git rebase -i`

普通 rebase 主要用于把提交移动到新的基底之上；交互式 rebase 则允许你编辑、重排、合并、删除尚未共享或适合重写的提交历史。

基本语法：

Bash

```
git rebase -i <commit>
```

这里的 `<commit>` 是变基范围的起点，而且这个起点本身通常不包含在待编辑列表中。

例如：

Bash

```
git rebase -i HEAD~3
```

意思是：打开最近三个提交的交互式编辑列表，不包含 `HEAD~3` 指向的提交。

如果最近三个提交是：

```
A ── B ── C ── D    HEAD
```

执行：

Bash

```
git rebase -i HEAD~3
```

待处理的通常是 `B`、`C`、`D`，而 `A` 是保留的基底。

Git 会打开编辑器，显示类似以下内容：

```
pick abc1234 B: add feature
pick def5678 C: fix feature
pick ghi9012 D: update docs

# Commands:
# p, pick
# r, reword
# e, edit
# s, squash
# f, fixup
# d, drop
```

这里最重要的规则是：

* 每行代表一个提交。

* 每行开头的命令决定 Git 如何处理该提交。

* 默认按从上到下的顺序处理。

* 修改完成后，保存并退出编辑器，Git 才会开始执行。

如果你使用 Vim，通常可以按 `i` 进入编辑模式，编辑完成后按 `Esc`，输入 `:wq` 保存退出。

下面我们逐个演示六种操作。

# 四、六种交互式变基操作详解

为了让每种操作都容易理解，我们使用统一的提交历史：

```
A ── B ── C ── D    HEAD
```

其中：

* `A`：初始代码。

* `B`：实现一个功能。

* `C`：修复功能中的小问题。

* `D`：更新文档。

我们准备执行：

Bash

```
git rebase -i HEAD~3
```

假设编辑器中显示：

```
pick bbbbbbb B: implement feature
pick ccccccc C: fix feature
pick ddddddd D: update docs
```

下面每个操作都从这个初始状态单独理解。实际练习时，请使用独立的测试仓库或在每次实验前恢复到相同状态，不要连续执行所有示例。

## 4.1 `pick`：保留提交

`pick` 是默认选项，意思是保留该提交，并按当前列表的顺序重放它。

```
pick bbbbbbb B: implement feature
pick ccccccc C: fix feature
pick ddddddd D: update docs
```

执行过程：

1. Git 以基底 `A` 为起点。

2. 重放 `B`。

3. 重放 `C`。

4. 重放 `D`。

最终历史：

```
A ── B' ── C' ── D'
```

为什么还是 `B'`、`C'`、`D'`，而不是原来的 `B`、`C`、`D`？

因为交互式 rebase 也会重新应用提交。即使使用 `pick`，在重写历史的情况下，提交 SHA 通常也会改变。

什么时候用？ 你希望保留某个提交，只是需要把它移动到新的基底，或者与其他提交一起整理历史时。

## 4.2 `reword`：修改提交信息

假设 `C` 的提交信息写得太随意了：

```
fix
```

你想把它改成更清晰的：

```
fix: handle empty input
```

将对应的 `pick` 改为 `reword`：

```
pick bbbbbbb B: implement feature
reword ccccccc fix
pick ddddddd D: update docs
```

保存并退出后，Git 会在处理到 `C` 时打开提交信息编辑器，让你修改提交说明。

修改后，历史类似：

```
A ── B' ── C' ── D'

C' 的提交信息：fix: handle empty input
```

这里有两个重点：

* `reword` 主要修改提交信息，不要求你修改代码内容。

* 因为提交信息属于提交对象的一部分，修改后 `C` 的 SHA 会改变；后续依赖它的提交通常也会被重建。

什么时候用？ 修正拼写错误、让提交信息符合团队规范、把 `fix` 改成 `fix: handle empty input` 等。

## 4.3 `edit`：暂停下来修改提交

这是六种操作中非常值得掌握的一种。

假设提交 `C` 不仅提交说明有问题，代码本身也需要修改。你可以这样写：

```
pick bbbbbbb B: implement feature
edit ccccccc C: fix feature
pick ddddddd D: update docs
```

保存退出后，Git 会重放 `B`，然后在 `C` 处暂停。

此时你可以执行：

Bash

```
# 查看当前状态
git status

# 修改文件，例如：
vim app.txt

# 将修改加入暂存区
git add app.txt

# 更新当前暂停的提交
git commit --amend
```

如果只想修改代码，而不改变原提交说明，可以使用：

Bash

```
git commit --amend --no-edit
```

接着继续：

Bash

```
git rebase --continue
```

Git 会继续重放 `D`，完成剩余变基过程。

整个流程可以理解为：

开始 rebase

重放 B

在 C 处暂停

修改文件 → git add → git commit --amend

执行 `git rebase --continue`

重放 D，完成变基

注意：`edit` 不会自动替你修改代码，它的作用是暂停，让你有机会修改当前提交。

什么时候用？ 修复某个历史提交里的代码、补上遗漏文件、调整该提交的实现等。

## 4.4 `squash`：合并提交，并编辑合并后的提交信息

假设你开发一个功能时，产生了三个提交：

```
A ── B ── C ── D
```

它们分别是：

* `B`：实现功能。

* `C`：修复一个小问题。

* `D`：补充遗漏的测试。

如果这三个提交本质上属于同一项功能，你可能不想在最终历史中保留三个独立提交。

编辑列表：

```
pick   bbbbbbb B: implement feature
squash ccccccc C: fix feature
squash ddddddd D: add missing tests
```

`squash` 的意思是：将当前提交与前一个保留的提交合并。

Git 会把这三个提交的更改合并起来，然后让你编辑最终提交信息。你可以将多个原始提交说明整理成一条：

```
feat: implement feature with tests
```

最终历史：

```
A ── B''
```

原来的 `B`、`C`、`D` 被整合为一个新提交 `B''`。

这里要特别注意：

`squash` 合并的是提交历史，不是简单地把几个提交说明拼接起来就结束了。 Git 会尝试组合这些提交的代码更改；如果发生冲突，你需要解决冲突后继续。

`squash` 通常需要跟在一个可以保留的提交后面，例如：

```
pick   B
squash C
squash D
```

如果第一行也写成 `squash`，通常会因为没有前一个用于合并的保留提交而报错。

什么时候用？ 把功能实现、补丁、测试等多个小提交整理成一个逻辑完整的提交，方便代码审查和维护。

## 4.5 `fixup`：合并提交，但丢弃被合并提交的信息

`fixup` 和 `squash` 很像，但它不会保留被合并提交的提交说明。

例如：

```
pick  bbbbbbb B: implement feature
fixup ccccccc fix typo
fixup ddddddd adjust test
```

这里 `B` 是主提交，`C` 和 `D` 都会被合并进 `B`。

最终历史：

```
A ── B''
```

最终提交信息仍然是：

```
B: implement feature
```

`C` 的 `fix typo` 和 `D` 的 `adjust test` 不会作为额外的提交说明保留。

如果你希望保留一条简洁的功能说明，同时把开发过程中的琐碎修正合并进去，`fixup` 往往比 `squash` 更方便。

| 对比             | `squash` | `fixup` |
| -------------- | -------- | ------- |
| 合并代码更改         | 是        | 是       |
| 合并后保留独立提交      | 否        | 否       |
| 是否需要编辑合并后的提交信息 | 通常需要     | 通常不需要   |
| 被合并提交的说明       | 可整理、合并   | 丢弃      |

有些 Git 版本也支持 `fixup -C`、`fixup -c` 等扩展形式，用于特殊的提交信息处理；一般先掌握普通 `fixup` 就足够了。

## 4.6 `drop`：从重写后的历史中删除提交

假设 `C` 是一个已经不再需要的实验性提交：

```
A ── B ── C ── D
```

编辑列表：

```
pick bbbbbbb B: implement feature
drop ccccccc C: experimental implementation
pick ddddddd D: update docs
```

执行后，Git 不会把 `C` 作为一个独立提交重放。

最终历史大致是：

```
A ── B' ── D'
```

但是要注意一个重要细节：如果 `D` 依赖 `C` 引入的代码，那么重放 `D` 时可能出现冲突，甚至因为代码依赖缺失而无法完成变基。

此外，`drop` 删除的是这段变基历史中的提交，并不代表立即从整个 Git 仓库中物理删除该提交对象。原提交可能暂时仍能通过其他引用或 reflog 找到。

什么时候用？ 删除误提交的调试代码、废弃的实验性提交、重复或不应进入最终历史的提交。

# 五、用一张图记住六种操作

选择一个操作，查看对应的变基编辑列表与结果。

### pick

### reword

### edit

### squash

### fixup

### drop

把当前提交合并到前一个保留的提交，并整理合并后的提交说明。

pick B

squash C

squash D

### B″

三个提交合并成一个，最终说明可以编辑。

# 六、进阶技巧：调整提交顺序

交互式 rebase 不只是修改提交类型，你还可以直接调整各行的顺序。

假设提交历史是：

```
A ── B ── C ── D
```

编辑列表默认是：

```
pick B: implement feature
pick C: fix feature
pick D: update docs
```

你可以将其改为：

```
pick B: implement feature
pick D: update docs
pick C: fix feature
```

Git 会按新顺序重放这些提交。

但这里要格外小心：提交顺序改变后，代码依赖关系可能发生变化。 比如 `C` 修复的是 `B` 引入的问题，那么把 `C` 移到 `B` 前面，可能无法应用，或者导致最终代码行为异常。

所以，调整顺序后不仅要检查 Git 是否成功完成，还要运行测试验证最终代码。

# 七、变基冲突怎么处理？

无论普通 rebase 还是交互式 rebase，都可能出现冲突。

例如：

Bash

```
git switch feature
git rebase main
```

假设 `main` 和 `feature` 都修改了同一个文件的同一段内容，Git 可能提示：

```
CONFLICT (content): Merge conflict in app.txt
error: could not apply ...
```

这时不用慌，按以下步骤处理。

1. 查看冲突状态

   `bash git status`

2. 打开冲突文件

   可能看到这样的内容：

   `text <<<<<<< HEAD main branch content ======= feature branch content >>>>>>> commit-being-replayed`

   在 rebase 过程中，`HEAD` 通常指向当前目标基底或已重放的历史；另一侧是正在重放的提交。不要仅凭 `ours`、`theirs` 的直觉选边，要结合实际代码判断。

3. 手动编辑文件

   保留正确的代码，并删除 `<<<<<<<`、`=======`、`>>>>>>>` 等冲突标记。

4. 标记冲突已解决

   `bash git add app.txt`

5. 继续变基

   `bash git rebase --continue`

   如果后面的提交再次发生冲突，就重复上述过程，直到完成。

如果发现操作方向错了，或者想放弃本次变基：

Bash

```
git rebase --abort
```

这会尝试将当前分支恢复到本次 rebase 开始之前的状态。开始操作前如果工作区已有未提交修改，仍然应该提前备份或妥善保存。

另外还有一个命令：

Bash

```
git rebase --skip
```

它会跳过当前正在重放的提交。只有确认该提交不需要保留时才应该使用，否则可能丢失需要的代码更改。

# 八、最实用的工作流：开发完后整理提交

假设你在自己的 `feature` 分支上开发了一个功能，期间产生了这些提交：

```
feat: add retrieval module
fix: fix typo
fix: handle empty input
test: add retrieval tests
docs: update readme
```

你想将历史整理为：

```
feat: add retrieval module
test: add retrieval tests
docs: update readme
```

可以先检查当前状态：

Bash

```
git status
git log --oneline --graph --decorate
```

然后确认目标分支已经更新：

Bash

```
git fetch origin
```

如果团队约定基于远程主分支开发，可以执行：

Bash

```
git rebase origin/main
```

接下来整理最近五个提交：

Bash

```
git rebase -i HEAD~5
```

假设编辑器中是：

```
pick   aaa1111 feat: add retrieval module
fixup  bbb2222 fix: fix typo
fixup  ccc3333 fix: handle empty input
pick   ddd4444 test: add retrieval tests
pick   eee5555 docs: update readme
```

保存退出后，两个小修复会并入功能提交，测试和文档提交则保持独立。

最后执行：

Bash

```
git log --oneline --graph --decorate
```

并运行项目测试。

如果这些提交以前已经推送到远程分支，那么 rebase 后提交 SHA 会发生变化，普通 `git push` 可能被拒绝。确认该分支只有你在维护、没有覆盖他人新提交后，可以使用：

Bash

```
git push --force-with-lease origin feature
```

`--force-with-lease` 比直接使用 `--force` 更安全：如果远程分支已经发生你本地未知的变化，它通常会拒绝覆盖。但它并不是绝对保险，因此共享分支仍然要格外谨慎。

# 九、最后总结：你应该怎么选择？

| 你的目的            | 推荐操作                    |
| --------------- | ----------------------- |
| 把当前分支更新到最新主分支之上 | `git rebase main`       |
| 保留提交，仅调整提交历史    | `pick`                  |
| 修改提交说明          | `reword`                |
| 修改某个历史提交中的代码    | `edit`                  |
| 将多个提交合并，并整理提交说明 | `squash`                |
| 合并琐碎提交，不保留其说明   | `fixup`                 |
| 删除不需要的提交        | `drop`                  |
| 调整提交顺序          | 在交互式列表中移动行              |
| 放弃正在进行的变基       | `git rebase --abort`    |
| 继续解决冲突后的变基      | `git rebase --continue` |

我最建议你记住下面这三条：

1. `git rebase main`：把当前分支的提交重新应用到 `main` 之上。

2. `git rebase -i HEAD~N`：整理最近 N 个提交，不包含 `HEAD~N` 指向的基底提交。

3. `squash` 与 `fixup` 的核心区别：前者允许整理合并后的提交说明，后者通常直接沿用前一个提交的说明。

最后一个工程实践原则：对尚未共享的个人开发分支，大胆整理历史；对已经被其他人依赖的共享分支，谨慎重写历史。

这条原则能帮你避开绝大多数 rebase 使用中的麻烦。
