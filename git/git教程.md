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