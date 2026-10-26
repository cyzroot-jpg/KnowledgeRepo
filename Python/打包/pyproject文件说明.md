# pyproject.toml 语法与功能详解

以演示包 `build_package/pyproject.toml` 为实例，系统讲一遍。

---

## 一、pyproject.toml 是什么

- **TOML 格式**的配置文件，位于项目根目录。
- 由 **PEP 518**（构建系统声明）和 **PEP 621**（项目元数据）定义。
- 是 Python 打包的**唯一权威配置**：构建后端、包信息、依赖、入口点都在这里。
- 替代了旧的 `setup.py` / `setup.cfg`。

---

## 二、TOML 基础语法（先懂这个才看得懂）

```toml
# 井号是注释
key = "字符串"                 # 字符串用双引号
num = 42                       # 整数
flag = true                    # 布尔
arr = ["a", "b"]               # 数组
inline = { name = "x", age = 1 }   # 行内表（花括号）

[project]                      # 表（table）：相当于一个 dict
name = "mygreet"               # [project] 下的键

[project.optional-dependencies]  # 子表（点号表示嵌套）
test = ["pytest"]

[[project.authors]]            # 双括号 = 数组里的表（列表套字典）
name = "Demo User"
```

一句话：`[a.b]` 是 **表**，`key = value` 是 **键值对**，`[[a]]` 是 **表数组**。

---

## 三、四个大区块总览

```toml
[build-system]      # ① 谁来构建（必备）
[project]           # ② 包是什么（元数据）
[project.*]         # ③ 各类附加信息（依赖/入口点/URL）
[tool.*]            # ④ 给某个工具/后端的私有配置
```

---

## 四、`[build-system]` —— 构建系统声明（PEP 518）

```toml
[build-system]
requires = ["setuptools>=61", "wheel"]   # 构建需要装的依赖
build-backend = "setuptools.build_meta"  # 后端入口：包.模块
```

| 键 | 作用 |
|---|---|
| `requires` | 构建时 pip 会在**隔离环境**装这些包 |
| `build-backend` | 真正执行构建的函数入口；不同后端不同（setuptools / hatchling / flit / poetry） |
| `backend-path` | 后端在当前项目内时的路径（少用） |

常见后端：`setuptools.build_meta`、`hatchling.build`、`flit_core.buildapi`、`poetry.core.masonry.api`。

---

## 五、`[project]` —— 核心元数据（PEP 621）

对照你的文件逐行说明：

```toml
[project]
name = "mygreet"                    # ★ 包名（PyPI 唯一，必填）
version = "0.1.0"                   # ★ 版本号（必填，除非用 dynamic）
description = "A tiny demo..."      # 一句话简介
readme = "README.md"                # 长描述文件（会进 long_description）
requires-python = ">=3.9"           # 支持的 Python 版本（pip 会检查）
authors = [{ name = "Demo User" }]  # 作者列表（表数组）
license = { text = "MIT" }          # 许可证
dependencies = []                   # ★ 运行依赖（装包时自动装）
```

### 字段全表

| 字段 | 类型 | 说明 |
|---|---|---|
| `name` | 字符串 | **必填**，包名 |
| `version` | 字符串 | 版本，如 `1.2.3`；或放 `dynamic` |
| `description` | 字符串 | 简介（≤ 一行） |
| `readme` | 字符串/表 | 长描述，可为文件名或内联文本 |
| `requires-python` | 字符串 | 如 `>=3.9,<4` |
| `license` | 字符串/表 | 见下方"许可证新写法" |
| `authors` | 表数组 | `[{name=..., email=...}]` |
| `maintainers` | 表数组 | 同上 |
| `keywords` | 数组 | 关键词，便于搜索 |
| `classifiers` | 数组 | 分类标签（Python 版本、许可证等） |
| `dependencies` | 数组 | 运行依赖，PEP 508 写法 `"requests>=2,<3"` |
| `urls` | 表 | 各种链接（见下） |
| `scripts` | 表 | 命令行入口（见下） |
| `gui-scripts` | 表 | GUI 入口 |
| `entry-points` | 子表 | 任意插件入口点（见下） |
| `dynamic` | 数组 | 声明哪些字段"构建时动态算"，不在此静态写 |

### 可选的写法细节

```toml
# authors 完整写法
authors = [
  { name = "Alice", email = "alice@example.com" },
  { name = "Bob" },
]

# readme 两种写法
readme = "README.md"
readme = { text = "这是长描述", content-type = "text/markdown" }

# 许可证：新旧写法
license = { text = "MIT" }                 # 旧（PEP 621 原版）
license = { file = "LICENSE" }             # 旧：从文件读
license = "MIT"                            # 新（PEP 639，SPDX 表达式）
license-files = ["LICENSE*"]               # 新：打包哪些许可证文件
```

> 建议：新项目用 `license = "MIT"`（SPDX），旧写法有 DeprecationWarning。

---

## 六、`[project.optional-dependencies]` —— 可选依赖

```toml
[project.optional-dependencies]
test = ["pytest"]
docs = ["sphinx", "myst-parser"]
all  = ["pytest", "sphinx"]
```

安装方式：

```bash
pip install mygreet              # 只装 dependencies
pip install "mygreet[test]"      # 加上 test 组的依赖
pip install "mygreet[test,docs]" # 多个组
```

---

## 七、`[project.scripts]` —— 命令行入口

```toml
[project.scripts]
mygreet = "mygreet.cli:main"     # 包.模块:函数
```

- `=` 左边是**终端命令名**，右边是 `模块:函数`。
- 装完后可直接跑 `mygreet`，等价于调用 `mygreet.cli.main()`。
- 构建后会生成 `entry_points.txt` 里的 `[console_scripts]`。

```toml
[project.gui-scripts]            # 无控制台窗口的 GUI 入口
mygui = "mygreet.gui:main"
```

---

## 八、`[project.entry-points]` —— 插件入口点（重点）

**任意命名分组**的入口点，vLLM 插件就是用它：

```toml
[project.entry-points."vllm.platform_plugins"]
sdaa = "vllm_sdaa:register"

[project.entry-points."vllm.general_plugins"]
tecovllm_models = "tecovllm_models:init"
```

- 组名带**点**或特殊字符时**必须加引号**。
- 与 `scripts` 的区别：`scripts` 是给用户敲命令用的；`entry-points` 是给**别的程序发现插件**用的（vLLM 会遍历 `vllm.general_plugins` 组）。
- 点号等价写法（两种等价）：

```toml
[project.entry-points."vllm.general_plugins"]
x = "pkg:init"
# 等价于
[project.entry-points.vllm.general_plugins]   # 不推荐，易歧义
```

---

## 九、`[project.urls]`

```toml
[project.urls]
Homepage = "https://example.com"
Repository = "https://github.com/me/mygreet"
Documentation = "https://docs.example.com"
Issues = "https://github.com/me/mygreet/issues"
```

键名随意（会显示在 PyPI 侧边栏）。

---

## 十、`[tool.*]` —— 后端/工具的私有配置

不属于 PEP 621，是**具体工具**的配置。setuptools 的常见项：

```toml
[tool.setuptools]
package-dir = { "" = "src" }          # src 布局映射

[tool.setuptools.packages.find]       # 自动发现包
where = ["src"]                       # 去哪找
include = ["mygreet*"]                # 只收这些
exclude = ["tests*"]                  # 排除

[tool.setuptools.package-data]        # 打包非 .py 文件（如模板、json）
mygreet = ["data/*.json"]

[tool.setuptools.dynamic]             # 配合 dynamic 字段
version = { attr = "mygreet.__version__" }
readme  = { file = "README.md" }
```

### `dynamic` 玩法（版本从代码里读）

```toml
[project]
name = "mygreet"
dynamic = ["version"]                 # 版本不写死

[tool.setuptools.dynamic]
version = { attr = "mygreet.__version__" }   # 从 mygreet/__init__.py 读 __version__
```

其他工具示例：

```toml
[tool.black]
line-length = 100

[tool.pytest.ini_options]
addopts = "-q"

[tool.ruff]
line-length = 100
```

---

## 十一、完整综合示例

```toml
[build-system]
requires = ["setuptools>=61"]
build-backend = "setuptools.build_meta"

[project]
name = "mygreet"
version = "0.1.0"
description = "A tiny demo package"
readme = "README.md"
requires-python = ">=3.9"
license = "MIT"
authors = [{ name = "Demo User", email = "demo@example.com" }]
keywords = ["demo", "greeting"]
classifiers = [
  "Programming Language :: Python :: 3",
  "License :: OSI Approved :: MIT License",
]
dependencies = ["click>=8"]

[project.optional-dependencies]
test = ["pytest"]

[project.scripts]
mygreet = "mygreet.cli:main"

[project.entry-points."vllm.general_plugins"]
mygreet = "mygreet:init"

[project.urls]
Homepage = "https://example.com"

[tool.setuptools.packages.find]
where = ["src"]
```

---

## 十二、速查：区块 ↔ 作用

| 区块 | 标准 | 作用 | 必填 |
|---|---|---|---|
| `[build-system]` | PEP 518 | 谁构建、装什么 | 不用 build 时可省 |
| `[project]` | PEP 621 | 包名/版本/依赖等 | `name` 必填 |
| `[project.optional-dependencies]` | PEP 621 | 可选依赖组 | 否 |
| `[project.scripts]` | PEP 621 | 命令行命令 | 否 |
| `[project.entry-points.*]` | PEP 621 | 插件入口（vLLM 插件） | 否 |
| `[project.urls]` | PEP 621 | 链接 | 否 |
| `[tool.xxx]` | 各工具 | 后端/工具私有配置 | 视后端 |

---

## 十三、常见坑

| 坑 | 说明 |
|---|---|
| 组名不加引号 | `[project.entry-points.vllm.general_plugins]` 会被 TOML 当嵌套表 → 报错，**必须加引号** |
| `readme` 引用的文件不存在 | 构建直接失败 |
| src 布局没配 `packages.find` | 打出空包 / import 不到 |
| `dependencies` 与 `optional-dependencies` 混用 | 前者必装，后者按组装 |
| `version` 同时静态写又进 `dynamic` | 冲突报错，二选一 |
| 用 `license = {text=...}` 旧写法 | 会有弃用警告，新项目用 SPDX 字符串 |

---

## 十四、一句话总结

`pyproject.toml` 就四块：**`[build-system]` 说谁来建，`[project]` 说包是什么，`[project.*]` 挂依赖/命令/插件入口，`[tool.*]` 放工具私有配置**。语法是 TOML（表 + 键值 + 数组表）；vLLM 插件靠的就是 `[project.entry-points."vllm.general_plugins"]` 这一块。



[project.entry-points] 是 pyproject.toml 里专门用来"声明入口点（插件/命令）"的标准子表，它是 setup.py 里 entry_points={...} 的声明式替代，由 PEP 621 定义。