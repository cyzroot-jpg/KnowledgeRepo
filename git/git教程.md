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

