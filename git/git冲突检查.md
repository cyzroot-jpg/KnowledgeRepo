老板，给你总结一套 Gerrit + Git 查找代码冲突的标准流程。以后提交代码前，照着执行就行。重点是：先检查冲突，不要一上来就 `git pull` 或 `git merge`。

# 一、最快的冲突检查方法（推荐）

你的仓库目标分支是 `main`，在项目目录执行：

第 1 步：获取远程最新代码

Bash

```
git fetch origin
```

第 2 步：检查本地提交与远程分支是否冲突

Bash

```
git merge-tree --write-tree HEAD origin/main
```

看输出中有没有：

```
CONFLICT (content): Merge conflict in .gitmodules
```

如果出现 `CONFLICT`，说明存在合并冲突；后面显示的就是冲突文件。

这个命令只模拟合并，不会修改当前工作区，也不会真正完成合并。

第 3 步：查看冲突文件的差异

例如你这次的冲突文件是 `.gitmodules`：

Bash

```
git diff HEAD origin/main -- ../../.gitmodules
```

注意：`git diff` 显示的是两边的差异，不代表每一处差异都一定是冲突；判断冲突应以 `git merge-tree` 的输出为准。

# 二、如何查看哪些提交存在差异？

你这次查到了两个不同的提交：

Bash

```
git log --oneline origin/main..HEAD
git log --oneline HEAD..origin/main
```

含义如下：

| 命令                          | 作用        |
| --------------------------- | --------- |
| `git log origin/main..HEAD` | 查看本地独有的提交 |
| `git log HEAD..origin/main` | 查看远程独有的提交 |

你实际查到的是：

* 本地：`979fe59 feat(moses-adapt): add moses-adapt`

* 远程：`7b708e6 feat(surfdesign-adapt): add SurfDesign-sdaa`

这说明双方各有一个独有提交，但提交不同不代表必然冲突，仍需执行 `git merge-tree` 判断。

# 三、如何定位具体冲突内容？

先找到冲突文件，再查看差异：

Bash

```
git diff HEAD origin/main -- ../../.gitmodules
```

如果要查看两边文件的完整版本：

Bash

```
git show HEAD:../../.gitmodules
git show origin/main:../../.gitmodules
```

你这次的情况是：

* 本地新增了 `moses` 子模块配置。

* 远程新增了 `SurfDesign` 子模块配置。

* `.gitmodules` 的相关内容无法被 Git 自动合并。

如果两个子模块都需要保留，就应该整合两段配置，而不是简单地选择本地或远程版本。

# 四、检查 Gerrit 上的 Change 是否冲突

这里要区分两种情况：

情况 A：检查本地提交与远程分支

使用：

Bash

```
git fetch origin
git merge-tree --write-tree HEAD origin/main
```

这就是你前面已经完成的检查。

情况 B：检查 Gerrit 上某个 Change

先在 Gerrit 页面确认：

* `Change` 对应的提交或最新 Patch Set

* `Destination Branch`，即目标分支

然后使用对应的提交 SHA 和目标分支进行检查。不要默认 Gerrit Change 一定对应当前的 `HEAD`。

# 五、以后可以直接记住的命令清单

下面这四条基本够用：

Bash

```
# 1. 获取远程最新信息
git fetch origin

# 2. 检查是否有合并冲突（不修改工作区）
git merge-tree --write-tree HEAD origin/main

# 3. 查看本地独有的提交
git log --oneline origin/main..HEAD

# 4. 查看远程独有的提交
git log --oneline HEAD..origin/main
```

## 最后记住三个要点

1. 查冲突： `git merge-tree --write-tree HEAD origin/main`

2. 找文件： 看输出中的 `CONFLICT`。

3. 看差异： `git diff HEAD origin/main -- 文件路径`。

如果只想检查冲突，就执行前两步，不需要真正合并。如果准备修复冲突，再根据提交状态选择 `merge`、`rebase` 或 Gerrit 对应的更新流程。
