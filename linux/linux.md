# Linux

## 1. md5sum

```bash
md5sum 源于 "MD5 message-digest algorithm"，即 MD5 消息摘要算法。这个命令用于计算和校验文件的 MD5 哈希值。MD5 是一种被广泛使用的密码学哈希函数，它将任意长度的数据映射为固定长度（128位）的哈希值，通常以32位十六进制数表示。md5sum 命令通过读取文件内容，使用 MD5 算法生成该文件的唯一“指纹”（哈希值）。这个指纹可以用于验证文件在传输或存储过程中是否发生更改。

> md5sum [OPTION]... [FILE]...

使用 md5sum 加文件名可以直接输出该文件的 MD5 值

使用 md5sum 加多个文件名可以输出多个文件的 MD5 值
```

## 2. yum使用

**语法：**

```bash
yum [options] [command] [package ...]

    - options：可选，选项包括-h（帮助），-y（当安装过程提示选择全部为 "yes"），-q（不显示安装的过程）等等。
    - command：要进行的操作。
    - package：安装的包名。

```

**常用命令：**

```bash

1. 列出所有可更新的软件清单命令：yum check-update

2. 更新所有软件命令：yum update

3. 仅安装指定的软件命令：yum install <package_name>

4. 仅更新指定的软件命令：yum update <package_name>

5. 列出所有可安裝的软件清单命令：yum list

6. 删除软件包命令：yum remove <package_name>

7. 查找软件包命令：yum search <keyword>

8. 清除缓存命令:

    - yum clean packages: 清除缓存目录下的软件包
    - yum clean headers: 清除缓存目录下的 headers
    - yum clean oldheaders: 清除缓存目录下旧的 headers
    - yum clean, yum clean all (= yum clean packages; yum clean oldheaders) :清除缓存目录下的软件包及旧的 headers

```

**无残留卸载软件**

```bash

yum remove 命令默认只卸载软件包本身，而会保留配置文件。

1. 卸载主软件包

yum remove <package name>

2. 清理无用的依赖包

yum autoremove
这个命令会自动查找并删除那些因安装该软件而被引入、但卸载后已不被任何其他软件需要的依赖包


3. 清理yum缓存

yum clean all
此命令会清除 yum 下载的软件包和元数据缓存，释放磁盘空间

4. 手动删除残留的配置文件与数据

这是实现“无残留”最核心的一步。软件通常会在以下目录留下配置文件、日志或数据:

    - 配置文件: /etc/<package_name>/
    - 数据目录: /var/lib/<package_name>/
    - 日志目录: /var/log/<package_name>/
    - 用户配置: ~/.config/<package_name>/, ~/.local/share/<package_name>/
```
## 3. source
source 是 shell（如 bash）的内置命令，作用是在当前 shell 环境中执行一个脚本文件，而不是新开一个子 shell 去执行。
用法：source filename 或 . filename
关键区别：直接运行 ./script.sh 会开一个子进程，脚本里设的变量、改的环境在脚本结束后就没了；而 source script.sh 相当于把脚本内容一行行贴到当前终端里执行，所以变量、cd、export 等会保留下来。
典型用途：加载环境配置，比如 source ~/.bashrc、source venv/bin/activate（激活 Python 虚拟环境）。

/root/.bashrc：root 用户的家目录下的 bash 配置文件。.bashrc 是隐藏文件（点开头），通常在每次打开交互式 bash shell 时自动加载。
你修改了 .bashrc（比如加了 alias、改了 PATH、加了环境变量），但当前终端不会自动感知。
这个时候需要进行执行`source .bashrc`让设置生效，就能让改动立刻在当前终端生效，不用关掉重开终端。
> . 是 source 的简写

*source和bash的区别:*
- source：在当前 shell 生效，变量保留。
- bash /root/.bashrc：开一个子 shell 执行，执行完就退出，改动不会留在当前终端。

## 4. top命令的结果
| top 中的位置 | 字段/列 | 你这里看到的值 | 含义 | 怎么看/通俗解释 |
|---|---|---|---|---|
| 第1行 | 当前时间 | 02:04:59 | 系统当前时间 | 就是此刻时间 |
| 第1行 | up | 110 days, 17:52 | 系统已运行时长 | 这台机器开机约 110 天 17 小时 52 分 |
| 第1行 | user | 0 user | 当前登录用户数 | 现在没有用户登录 |
| 第1行 | load average | 35.71, 36.41, 36.22 | 过去 1、5、15 分钟平均负载 | 不是 CPU 百分比；高不高要看 CPU 核数。你这里 CPU 很闲但 load 高，说明很多任务在等 I/O、GPU、NFS 或内核资源 |
| 第2行 | Tasks total | 47 total | 总任务数 | 当前共有 47 个进程/任务 |
| 第2行 | running | 1 running | 正在运行的任务数 | 只有 1 个在真正跑 |
| 第2行 | sleeping | 46 sleeping | 睡眠/等待中的任务数 | 大多数进程都在等，通常包括 S 和 D 状态 |
| 第2行 | stopped | 0 stopped | 已停止的任务数 | 没有暂停的进程 |
| 第2行 | zombie | 0 zombie | 僵尸进程数 | 没有僵尸进程，正常 |
| 第3行 | us | 2.2 us | 用户态 CPU 占用 | 普通程序占 CPU 很少 |
| 第3行 | sy | 1.2 sy | 内核态 CPU 占用 | 系统内核占 CPU 很少 |
| 第3行 | ni | 0.0 ni | nice 调整过优先级的进程占用 | 没有这类进程占 CPU |
| 第3行 | id | 96.4 id | CPU 空闲率 | CPU 非常闲，96.4% 空闲 |
| 第3行 | wa | 0.0 wa | 等待 I/O 的 CPU 时间 | 表面看没有 I/O 等待，但 D 状态进程不一定体现在这里 |
| 第3行 | hi | 0.2 hi | 硬中断占用 | 很少 |
| 第3行 | si | 0.1 si | 软中断占用 | 很少 |
| 第3行 | st | 0.0 st | 被虚拟化偷走的时间 | 没有或几乎没有 |
| 第4行 | MiB Mem total | 1037131.+total | 总内存 | 约 1013 GiB，约 1 TiB，内存非常大 |
| 第4行 | free | 80995.6 free | 完全空闲内存 | 约 79 GiB |
| 第4行 | used | 67811.4 used | 已用内存 | 约 66 GiB |
| 第4行 | buff/cache | 900945.8 buff/cache | 缓存/缓冲内存 | 约 880 GiB，可被回收，不算真正紧张 |
| 第5行 | Swap total | 0.0 total | 交换分区总量 | 没有 Swap |
| 第5行 | Swap free | 0.0 free | 空闲 Swap | 没有 Swap |
| 第5行 | Swap used | 0.0 used | 已用 Swap | 没有使用 Swap |
| 第5行 | avail Mem | 969319.9 avail Mem | 可用内存 | 约 947 GiB，内存完全不是瓶颈 |
| 进程表 | PID | 120287 等 | 进程 ID | 每个进程的唯一编号 |
| 进程表 | USER | root | 运行用户 | 这些进程都是 root 用户运行的 |
| 进程表 | PR | 20 | 进程优先级 | 普通优先级 |
| 进程表 | NI | 0 | nice 值 | 0 表示默认优先级，数值越小优先级越高 |
| 进程表 | VIRT | 2200.8g 等 | 虚拟内存 | 通常很大，不代表真实占用 |
| 进程表 | RES | 11.1g 等 | 常驻物理内存 | 这才是进程真实占用的内存 |
| 进程表 | SHR | 794880 等 | 共享内存 | 和其他进程共享的内存部分 |
| 进程表 | S | D / S | 进程状态 | R=运行，S=睡眠，D=不可中断睡眠，Z=僵尸；D 通常表示卡在等 I/O、GPU、NFS 或内核锁 |
| 进程表 | %CPU | 82.1 等 | CPU 使用率 | 是刷新时的占用比例，多核机器可能超过 100% |
| 进程表 | %MEM | 1.1 等 | 物理内存占比 | 占整个物理内存的百分比 |
| 进程表 | TIME+ | 18:05.65 等 | 累计 CPU 时间 | 不是运行了多久，而是累计消耗的 CPU 时间 |
| 进程表 | COMMAND | python 等 | 命令名 | 进程运行的程序 |
| 具体进程 | 120287 | python，D，82.1%CPU，11.1g RES | 主 python 进程 | 最可疑：处于 D 状态，说明它卡在不可中断等待，重点查 I/O、GPU、NFS、内核锁 |
| 具体进程 | 120491 | pt_data_worker，S，12.0%CPU，8.9g RES | PyTorch 数据加载 worker | 通常和 python 训练/推理进程相关 |
| 具体进程 | 103259 | opencode，S，2.7%CPU，1.2g RES | 某个工具进程 | 基本不活跃 |
| 具体进程 | 1 | bash，S | 初始/父进程 | 容器或系统里的 1 号进程，通常是 bash |
| 总体结论 | - | load 高，但 CPU 96.4% 空闲 | 瓶颈不在 CPU | 内存充足，CPU 很闲，重点是查 PID 120287 的 python 为什么进入 D 状态 |
