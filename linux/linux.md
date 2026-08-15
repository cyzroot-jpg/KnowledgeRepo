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