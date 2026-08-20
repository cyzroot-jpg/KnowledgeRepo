# Git命令使用


```bash

1. 将要提交的文件添加到缓存区
    git add .  # 将全部文件添加到缓存区
    git add 修改的文件  # 将指定的文件添加到缓存区

2. 配置提交用户的信息
    git config --global user.name 'xxxx'
    git config --global user.email 'xxx.xxx'

3. 将缓存区中的文件提交到本地仓库
    git commit -m '提交的信息'

4. 将本地仓库上传到远程仓库
    git push origin（远程仓库的别名，默认是这个） main


```

```bash
在本地初始化仓库，并提交到远程仓库

1. 初始化仓库
    git init
    在项目目录下面生成`.git`文件夹

2. 设置提交的用户信息
    git config --global user.name 'xxxx'
    git config --global user.mail 'xxx.xxx'

3. 设置远程仓库
    git remote add 远程仓库别名(默认origin) 远程仓库地址

4. 查看配置的远程仓库
    git remote -v

5. 将要提交的文件添加到缓存区
    git add . # 将全部的文件都添加到缓存区
    git add 指定的文件

6. 将缓存区的文件提交到本地仓库
    git commit -m '提交的信息'

7. 查看分支
    git branch
    > 注意： 有的版本的git在初始化仓库的时候的默认分支是master，而现在的默认的分支是main

8. 将本地仓库提交到远程仓库中
    git push 远程仓库的别名 本地仓库的分支:远程仓库的分支
    > 如果本地仓库的分支和远程仓库的分支一样就写一个就行


补充：
分支的操作：

1. 创建新分支并切换到新分支
    git checkout -b 分支名字

2. 切换分支
    git checkout 分支名

3. 查看分支
    git branch

4. 查看远程分支
    git branch -r

5. 查看所有本地和远程分支
    git branch -a

6. 合并分支
    git merge 分支名a
    将a分支合并到当前分支

7. 删除分支
    git branch -d 分支名

8. 删除远程分支
    git push origin --delete 分支名

9. 强制删除未合并的分支
    git branch -d 分支名

10. 在clone远程仓库的时候，先切换分支在clone
    git clone -b 远程仓库地址

```

# GitHub配置SSH密钥

> 密码/Token 是你“背诵”的门禁密码（会被别人偷看），SSH 密钥是你“持有”的加密门禁卡（数学芯片无法复制）。

```bash
1. windows打开Git Bash
ssh-keygen -t rsa -b 4096 -C "github的注册邮箱"
生成完成后，该目录下就会出现两个文件：id_rsa（私钥）和 id_rsa.pub（公钥）。

2. 复制公钥内容
cat ~/.ssh/id_rsa.pub

3. 将公钥添加到GitHub中
- 登录github，点击设置
- 菜单中的SSH and GPG keys
- 点击New SSH Key
- Title 随便填， Key粘贴刚才复制的内容
- 点击Add SSH Key

4. 测试连接
ssh -T git@github.com
如果看到 Hi 用户名! You've successfully authenticated...，说明大功告成。

5. 重新执行克隆
git clone xxxxxxxx

```

# git push时出现了网络问题
> fatal: unable to access 'https://github.com/cyzroot-jpg/KnowledgeRepo.git/': Failed to connect to github.com port 443 after 21034 ms: Could not connect to server

```bash
原因是我使用了vnp导致，开过代理导致的本机系统端口号和 git的端口号不一致导致的。

关闭代理即可

```

# Git status

```bash
git status 是一个用于查看 Git 仓库当前状态的命令。

git status 命令可以查看在你上次提交之后是否有对文件进行再次修改。

git status 命令会显示以下信息：

- 当前分支的名称。
- 当前分支与远程分支的关系（例如，是否是最新的）。
- 未暂存的修改：显示已修改但尚未使用 git add 添加到暂存区的文件列表。
- 未跟踪的文件：显示尚未纳入版本控制的新文件列表。

通常我们使用 -s 参数来获得简短的输出结果：

$ git status -s
AM README
A  hello.php

AM 状态的意思是这个文件在我们将它添加到缓存之后又有改动。
```

# Git show

```bash
git show 命令用于显示 Git 对象的详细信息。

git show 命令用于查看提交、标签、树对象或其他 Git 对象的内容。这个命令对于审查提交历史、查看提交的具体内容以及调试 Git 对象非常有用。

```

# Git pull PR

>  PR 拉到本地做“真机测试”

```bash

方法一：使用 GitHub CLI（最省心，强烈推荐）

如果你装了 gh 命令行工具，这是最完美的测试流程：

一键拉取（假设 PR 编号是 567）：

gh pr checkout 567

这条命令会自动下载 PR 的代码，自动切换到该 PR 对应的分支，还会自动帮你把本地环境和远端 PR 关联好。


方法二：通用 Fetch 法（不需要装 gh，最通用）

如果你没有装 gh，用原生 Git 命令也很简单：

拉取 PR 代码到本地新分支（假设 PR 编号是 567，本地起个名字叫 test-pr-567）：

git fetch origin pull/567/head:test-pr-567

    ① git fetch：核心动作。意思是“只下载，不合并且不切换分支”。它只把远端缺失的对象（commits、文件）拖到你的本地仓库里。

    ② origin：远程仓库的别名。通常指你克隆代码时那个默认的远程地址。

    ③ pull/567/head：数据源头。指服务器上“编号 567 这个 PR 的最新源分支代码”（我们之前聊过，这是 GitHub 服务器自动生成的虚拟引用）。

    ④ :（冒号）：分界线。冒号左边是“远端的东西”，冒号右边是“本地要放的位置”。

    ⑤ test-pr-567：本地目标。就是你在本地仓库里要新建/更新的分支名字。

在 GitHub 上，除了 pull/567/head 是固定的，还有一个固定写法叫 pull/567/merge。

 - pull/567/head：永远指 PR 作者提交的最新源码（可能会因为作者的后续推送而改变）。

 - pull/567/merge：指 如果系统现在自动把 PR 合并进主干，生成的那个“模拟合并结果”。


切换到该分支：

git checkout test-pr-567


```


# Git fetch

```bash

git pull 完整展开后，其实就是 git fetch + git merge 的连续执行。


如果你执行 git fetch origin main：
Git 会去远端把最新的代码下载到你的本地仓库缓存区（.git 文件夹里）。但是，你当前正在看（工作区）的代码文件不会发生任何变化。你依然在写旧的代码，只是 Git 悄悄告诉你：“嘿，我拿到新货了，在仓库里放着呢，你随时可以看。”

如果你执行 git pull origin main：
Git 做完上面那步下载后，立刻自动执行了合并。它会强行把你当前分支上旧代码的位置，移动到刚下载的新代码位置。你的工作区文件会被直接修改成最新的内容。


git pull 并不是 100% 必须“合并（Merge）”，它也可以“变基（Rebase）”。

默认情况下，pull 确实等于 fetch + merge。

但是，如果项目要求保持线性历史，很多人会设置 git pull --rebase。此时，pull 就等于 fetch + rebase（变基是把你的本地提交“挪”到最新代码的屁股后面，而不是产生一个合并节点）。

不过，无论后面跟的是 merge 还是 rebase，你“pull 会比 fetch 多出修改本地代码的动作”


```

```bash

解释一下rebase

先设定一个场景（方便理解）
假设你和同事都从主分支（main）出发写代码：

同事动作快：他已经提交了 C，并推到了远端（origin/main）。

你的动作慢：你在本地提交了 A 和 B（此时你的本地 main 指向 B，但远端已经前进到 C 了）。

现在的状态是：你的本地分支（B）落后于远端分支（C），就像下图这样：

text
时间线从旧到新 （左 → 右）

main（远端）:  ...---C
              /
             /
main（本地）: ...---A---B
情况一：普通 git pull（默认 = fetch + merge）
如果你执行 git pull，Git 会把远端的新代码 C 拉下来，然后在你本地产生一个“合并节点（Merge Commit）”。

效果图如下：

text
main（本地）:  ...---A---B---M
              \         /
               ---C-----
“产生合并节点”：看到了吗？那个 M 就是新生成的合并提交。它有两个爹（B 和 C），表示“我把两条线缝在一起了”。

结果：提交记录像树杈一样分叉又合拢，历史是非线性的（像河流分了叉又汇合）。如果项目人多，时间长了这个图会乱得像毛线团。

情况二：git pull --rebase（ = fetch + rebase）
如果你执行 git pull --rebase，Git 会把远端的新代码 C 拉下来，但不产生合并节点。它会把你本地的提交 A 和 B 从原来的位置“剪切”下来，重新“粘贴”到最新的 C 后面。

效果图如下：

text
main（本地）:  ...---C---A'---B'
“挪到最新代码的屁股后面”：看！你的提交 A 和 B，现在排在了 C 的屁股后面（后面）。

“不产生合并节点”：因为 A 和 B 直接接在 C 后面，没有分叉，所以完全不需要 M 那个合并提交。

结果：提交记录像一根笔直的糖葫芦，只有一条主线，历史是线性的（从头到尾一条直线）。

```

# git merge
```bash




```

# git的提交历史

```json

*   e26c5dd (HEAD -> main, origin/main, origin/HEAD) Merge pull request #3 from cyzroot-jpg/cyz
|\  
| * e5c13db 提交git
|/  
*   a916a6f Merge pull request #2 from cyzroot-jpg/cyz
|\  
| *   86cdd4c Merge branch 'main' into cyz
| |\  
| |/  
|/|   
* |   a91bfea Merge pull request #1 from cyzroot-jpg/cyz
|\ \  
* | | 5e15e55 添加yum命令
* | | e4bf6b2 添加commit 命令
* | | 4dfbb76 docker文档更新new version
* | | c4a0635 Linux更新
* | | 309d447 C++提交
* | | 6e73dd8 更新git 命令
| | * a7d846d git更新git状态
| |/  
| * c64acc0 提交python文档
|/  
* 2f12d15 opencode的理解文档
* 08fff6e 更新README.md
* 30a8bc5 更新README.md
* 4b66073 提交C++w文档
* b4fc2d1 更新README文档
* 77b58d9 添加了git push 开代理导致的网络问题
* d00c8a7 提交开源项目学习文档--opencode agent的学习文档
* 29ca992 添加SSH密钥认证教程
* c9e2a99 first submit npm md
* bd9a456 first Docker, git, opencode, skill编写, Win安装opencode及连接微信
* 0f313a0 Initial commit

```


# git merge

```bash

git merge 就是用于从指定的commit合并到当前分支

> 这里的指定的commit是指从这些历史commit节点开始，一直到当前分开的时候。


```
> ----

```bash

git merge命令的两种用途：
    - 用于git pull中，来整合另一个仓库中的变化。 git pull = git fetch + git merge
    - 用于从一个分支到另一个分支的合并


如下例子：
     A<---B<---C topic   
     |   
D<---E<---F<---G master

当前分支为master

git merge topic将会把在master分支上二者共同的特点(E节点)之后分离的节点(即topic分支的A,B,C节点)重现在master分支上，直到topic分支当前的commit节点(C节点)，并位于master分支的顶部。并且沿着master分支和topic分支创建创建一个记录合并结果的新节点，该节点带有用户描述合并变化的信息。
```

> ----

**git merge相关的选项参数**

```bash

git merge的命令中，有一下三种使用参数：

 - git merge [-n] [--stat] [--no-commit] [--squash] [--[no-]edit] [-s <strategy>] [-X <strategy-option>] [-S[<keyid>]] [--[no-]rerere-autoupdate] [-m <msg>] [<commit>...]
 - git merge <msg> HEAD <commit>...
 - git merge --abort


参数：
    --commit和--no-commit
        --commit参数使得合并后产生一个合并结果的commit节点。该参数可以覆盖--no-commit。
        --no-commit参数使得合并后，为了防止合并失败并不自动提交，能够给使用者一个机会在提交前审视和修改合并结果。

    --edit和-e以及--no-edit
        --edit和-e用于在成功合并、提交前调用编辑器来进一步编辑自动生成的合并信息。因此使用者能够进一步解释和判断合并的结果。
        --no-edit参数能够用于接受自动合并的信息（通常情况下并不鼓励这样做）。
        如果你在合并时已经给定了-m参数（下文介绍），使用 --edit（或-e）依然是有用的，这将在编辑器中进一步编辑-m所含的内容。旧版本的节点可能并不允许用户去编辑合并日志信息。

    其他的参数：
    > https://www.cnblogs.com/dreamboycx/p/16012172.html
    
```


**git merge <msg> HEAD <commit>...**

```bash
在新版本中，应该使用 git merge -m <msg> <commit>...进行代替
```

**git merge --abort**

```bash

这个命令仅仅在合并后导致冲突时才用。这个命令将会抛弃合并过程并且尝试重建合并前的状态。
但是，当合并开始时如果存在未commit的文件，git merge --abort 在某些情况下将无法从西安合并前的状态。（特别是这些未commit的文件在合并的过程中将会被修改时）

> 警告：运行git-merge时含有大量的未commit文件很容易让你陷入困境，这将使你在冲突中难以回退。因此非常不鼓励在使用git-merge时存在未commit的文件，建议使用git-stash命令将这些未commit文件暂存起来，并在解决冲突以后使用git stash pop把这些未commit文件还原出来。

```

> ----
git的分支模型
> https://www.jianshu.com/p/b357df6794e3