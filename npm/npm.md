# npm教程

## 1. 配置npm的下载安装位置以及配置镜像源

**修改npm的全局路径**
```bash
1.在D盘创建自定义存放路径
mkdir D:\xxx\node_global

mkdir D:\xxx\node_cache


2. 配置npm全局路径与缓存路径
npm config set prefixe "D:\xxx\node_global"
npm config set cache "D:\xxx\node_cache"

3. 验证配置是否生效
npm config get prefix

输出配置的路径即可

4. 手动修改系统的环境变量
在用户变量中的Path，新增D:\node_global
重启终端

```

**配置永久全局npm国内镜像源**
```bash
1. 设置国内镜像源
npm config set registry https://registry.npmmirror.com # 阿里源

2. 验证镜像源
npm config get registry
输出配置的内容即可

```