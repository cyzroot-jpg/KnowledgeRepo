# Win安装opencode及连接微信

## 1. 安装nodejs

测试安装状态：

> npm -v
> node -v

## 2. 将NPM全局路径迁移到D盘
> npm默认全局路径为C盘，长期安装工具会导致C盘爆满，本次修改将全局安装、缓存路径迁移到C盘

**1. 在D盘创建自定义存放目录**
```bash
mkdir D:\node_global

mkdir D:\node_cache

```

**2. 配置npm全局路径与缓存路径**

```bash
npm config set prefix "D:\node_global"

npm config set cache "D:\node_cache"

```

**3. 验证配置是否生效**

```bash
npm config get prefix

```
当输出设置的路径即可

**4. 手动设置系统环境变量**

```bash
1. win的环境变量设置面板

2. 编辑用户变量中的Path，新增路径：D:\node_global

3. 关闭所有终端重新打开

```

## 3. 配置永久全局NPM国内镜像源

**1. 设置国内镜像源**

```bash
npm config set perfix registry https://registry.npmmirror.com

```

**2. 验证镜像源**

```bash
npm config get registry

```

> 配置优势： 全局、永久生效，无需为单个项目单独配置，所有`npm install`、脚手架工具均走国内高速通道

[备用指令]切回官方源

```bash
npm config set registry https://registry.npmjs.org

```

## 4. 安装opencode全局工具

> 前面的配置全部完成后，在安装opencode，会自动安装到D盘自定义目录

**全局安装命令**

```bash
npm install -g opencode-ai

```

**安装完成验证**

```bash
opencode --version

```

> opencode的实际安装路径：D:\node_global\node_modules\opencode-ai

## 5. opencode启动方式

> 所有终端均可直接启动

**1. 直接进入交互式主界面**

```bash
opencode

```

**2. 快速问答模式**

```bash
opencode ask 问题

```

**3. 项目对话模式**

```bash
opencode chat

```

## 6. opencode核心高频命令

> 进入主交互界面后，无需重复输入指令

| 分类 | 命令 | 说明 |
|------|------|------|
| 项目核心命令 | `/init` | 项目初始化（必用），扫描目录、识别技术栈 |
| 文件操作 | `/open 文件名` | 打开本地文件进行编辑分析 |
| | `/save` | 保存当前修改的代码 |
| | `/list` | 查看当前项目所有文件 |
| | `/run` | 直接运行当前代码文件 |
| 代码优化 | `/debug` | 自动排查代码报错、修复BUG |
| | `/refactor` | 一键重构代码、规范格式 |
| | `/test` | 自动生成对应单元测试用例 |
| 会话管理 | `/new` | 新建代码文件、初始化项目模板 |
| | `/clear` | 清空当前对话记录 |
| | `/help` | 查看全部内置命令 |
| | `/exit` | 退出OpenCode交互界面 |

**1. 项目核心命令**

```json
/init : 项目初始化命令
    - 自动扫描项目目录、识别技术栈、生成项目配置文件
    - 让AI读懂你的项目结构、代码规范、后续修改代码更精确
    - 进阶用法： /init 描述项目技术栈

```

**2. 文件与运行命令**

```json
- /open 文件名： 打开本地文件进行编辑分析
- /save 保存当前修改的代码
- /list 查看当前项目所有文件
- /run 直接运行当前代码文件
- /debug 自动排查代码报错，修复BUG 

```

**3. 代码优化命令**

```json
- /refactor 一键重构代码，精简冗余逻辑，规范代码格式
- /test 自动生成对应单元测试用例

```

**4. 基础会话命令**

```json
- /new 新建代码文件、初始化项目模板
- /clear 清空当前对话记录
- /help 查看全部内置命令
- /exit 推出opencode
```



# opencode连接微信

## 1. 安装cc-connect

```json
cc-connect 把运行在你机器上的 AI Agent 桥接到你日常使用的即时通讯工具。代码审查、资料研究、自动化任务、数据分析 —— 只要 AI Agent 能做的事，都能通过手机、平板或任何有聊天应用的设备来完成。

```

通过npm安装：

> npm install -g cc-connect


## 2. 配置

```bash
D:\Tools\nodejs\node_cache>cc-connect web Config file not found: C:\Users\X0261\.cc-connect\config.toml
Run cc-connect first to create a default config.

```
> cc-connect的配置文件就是默认在用户目录下面，windows就是在C盘

```bash
第一次运行cc-connect需要创建一个配置文件

- 1. 在用户目录下面创建 `.cc-connect`目录
- 2. 在上面创建的目录中创建并编辑配置文件，`config.toml`
> 这个配置文件可以从cc-connect的github中复制默认的，然后在进行修改 `config.example.toml`

```

在项目里面配置：
```bash
admin_from = "alice,bob" 设置了这个，只有这些用户ID才能执行/dir、/shell等权限命令

执行 /dir reset 时，cc-connect 会恢复配置中的 work_dir，并清除保存在 data_dir/projects/<project>.state.json 里的目录覆盖状态。

```