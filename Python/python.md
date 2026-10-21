# Python调用C++代码
## 1. 什么是pybind11
pybind11 是一个轻量级、只包含头文件的库，用于在 C++ 和 Python 之间创建绑定。它是 C++11 标准下重写 Boost.Python 的成果，核心思想是：用现代 C++ 的模板元编程自动推导类型并生成 Python 包装代码，你只需声明"暴露什么"，不用手写引用计数和类型转换。
- 依赖：仅需 C++11 编译器 + Python 开发头文件
- 许可证：BSD
- 类型转换、异常、STL 容器、智能指针、numpy 支持大多自动完成

1. 安装
pip 安装（最快）
pip install pybind11
python -m pybind11 --includes   # 查看头文件包含路径
或通过 CMake（推荐工程化使用）
find_package(pybind11 CONFIG REQUIRED)


1. 最小示例
example.cpp:
#include <pybind11/pybind11.h>

int add(int a, int b) {
    return a + b;
}

std::string greet(const std::string& name) {
    return "Hello, " + name + "!";
}

PYBIND11_MODULE(example, m) {
    m.doc() = "pybind11 example plugin";   // 模块文档
    m.def("add", &add, "A function that adds two numbers");
    m.def("greet", &greet, "Greet someone");
}

关键点：
- 宏 PYBIND11_MODULE(模块名, 变量m) 定义入口，模块名必须与生成的 .so 文件名一致
- m.def("Python中的名字", &C++函数指针, "文档")
编译（手动）:
c++ -O3 -Wall -shared -std=c++11 -fPIC \
    $(python3 -m pybind11 --includes) \
    example.cpp -o example$(python3-config --extension-suffix)
使用:
import example
print(example.add(1, 2))       # 3
print(example.greet("World"))  # Hello, World!

3. 用 CMake 编译（推荐）
cmake_minimum_required(VERSION 3.15)
project(example)

find_package(pybind11 REQUIRED)

pybind11_add_module(example example.cpp)
pybind11_add_module 会自动处理后缀、编译选项、链接等。

4. 绑定函数的高级用法
// 默认参数
m.def("mul", &mul, py::arg("a"), py::arg("b") = 1);

// 关键字参数
m.def("fn", &fn, "doc", py::arg("x"), py::arg("y"), py::arg("z") = 0.0);

// 返回引用 / 生命周期
m.def("get_ref", &get_ref, py::return_value_policy::reference);

// lambda 直接绑定（无需独立函数）
m.def("square", [](int x) { return x * x; });

// 绑定重载函数（需显式指定类型）
m.def("over", static_cast<int(*)(int)>(&over));
m.def("over", static_cast<int(*)(int,int)>(&over));

// 异常：C++ 异常自动转成 Python 异常
// std::runtime_error -> RuntimeError, std::out_of_range -> IndexError 等
m.def("boom", []() { throw std::runtime_error("failed"); });

5. 绑定类
struct Pet {
    Pet(const std::string& name) : name_(name) {}
    void setName(const std::string& name) { name_ = name; }
    const std::string& getName() const { return name_; }
    std::string name_;
};

PYBIND11_MODULE(example, m) {
    py::class_<Pet>(m, "Pet")
        .def(py::init<const std::string&>())      // 构造函数
        .def_readwrite("name", &Pet::name_)       // 可读写属性
        .def("setName", &Pet::setName)            // 方法
        .def("getName", &Pet::getName)
        .def("__repr__", [](const Pet& p) {       // 魔术方法
            return "<Pet named '" + p.name_ + "'>";
        });
}
p = example.Pet("Milo")
p.name = "Bob"
print(p.getName())   # Bob

6. 继承与虚函数
struct Animal { virtual std::string bark() const { return "?"; } };
struct Dog : Animal { std::string bark() const override { return "woof"; } };

py::class_<Animal>(m, "Animal")
    .def(py::init<>())
    .def("bark", &Animal::bark);

// Dog 继承 Animal，并允许 Python 端重写（若需要）
py::class_<Dog, Animal>(m, "Dog")
    .def(py::init<>());

7. 自动类型转换
STL 容器（需 include 对应头文件）:
#include <pybind11/stl.h>
std::vector<int> v = {1,2,3};
m.def("list_to_vec", [](std::vector<int> v){ ... });
m.def("get_vec", []() { return std::vector<int>{1,2,3}; });
list↔vector、dict↔map、set、tuple↔pair 均自动转换。
Numpy:
#include <pybind11/numpy.h>
m.def("sum", [](py::array_t<double> arr) {
    auto r = arr.unchecked<1>();          // 无边界检查的快速访问
    double s = 0;
    for (py::ssize_t i = 0; i < r.shape(0); i++) s += r(i);
    return s;
});
零拷贝访问 numpy 内存，适合高性能数值计算。

8. 智能指针与生命周期
#include <pybind11/stl.h>
class Foo { ... };
m.def("make_foo", []() { return std::make_shared<Foo>(); });  // 自动转 Python 对象
std::shared_ptr / unique_ptr 可自动转换为 Python 的引用计数管理，避免内存泄漏。

9. 一个完整的工程示例
目录结构：
project/
├── CMakeLists.txt
├── src/math.cpp
└── python/test.py
src/math.cpp:
#include <pybind11/pybind11.h>
#include <pybind11/stl.h>
namespace py = pybind11;

class Calculator {
public:
    Calculator(double init = 0) : value_(init) {}
    double add(double x) { value_ += x; return value_; }
    double value() const { return value_; }
private:
    double value_;
};

PYBIND11_MODULE(mathlib, m) {
    py::class_<Calculator>(m, "Calculator")
        .def(py::init<double>(), py::arg("init") = 0)
        .def("add", &Calculator::add)
        .def_property_readonly("value", &Calculator::value);
}
CMakeLists.txt:
cmake_minimum_required(VERSION 3.15)
project(mathlib)
find_package(pybind11 REQUIRED)
pybind11_add_module(mathlib src/math.cpp)
编译与使用：
mkdir build && cd build
cmake .. -Dpybind11_DIR=$(python3 -m pybind11 --cmakedir)
make
from mathlib import Calculator
c = Calculator(10)
print(c.add(5), c.value)   # 15.0 15.0

## 2. python打包
python的打包工具：setuptools

Python 没有编译产物，代码要能分发、能被别的程序 `import`，就必须做成一个"**分发包**"。所谓打包，就是：

```
一堆 .py 源码目录  ──构建工具加工──▶  可安装的包（带元数据 + 入口点）
```
python打包标准中，有两个角色：前端和后端。
前端：的描述是谁发起构建。
> 用户直接运行的那条命令/工具，负责组织和调整整个构建、安装过程。
常见的前端：
| 前端 | 说明 |
|---|---|
| pip | `pip install` / `pip wheel` |
| build | `python -m build` |
| uv | `uv build` / `uv pip install` |
| tox / nox | 自动化测试里触发构建 |

前端不关心，你的包的内部怎么写，它只做流程：
1. 读 pyproject.toml 的 [build-system].requires
2. 建一个隔离环境，把 requires 装进去
3. 找到 build-backend 指向的后端
4. 调用后端的标准"钩子函数"（如 build_wheel()）
5. 拿到后端交出的 .whl/.tar.gz，再决定安装/摆放

后端：描述谁真正执行构建。
真正懂怎么把一个项目构建成分发包的库。它实现一组标准钩子
build_wheel()          -> 生成 .whl
build_sdist()          -> 生成 .tar.gz
get_requires_for_build_wheel() -> 附加依赖
prepare_metadata_for_build_wheel() -> 提前产出元数据

常见后端：
| 后端 | 对应 build-backend |
|---|---|
| setuptools | `setuptools.build_meta` |
| Hatchling | `hatchling.build` |
| Flit | `flit_core.buildapi` |
| Poetry | `poetry.core.masonry.api` |

它读什么：pyproject.toml 里的 [project]（名字、版本、依赖……）和 [tool.xxx]（自己的专属配置），然后负责把源码/元数据/入口点打包。

前后端如何配合：（一次python -m build的过程）
你
 │  运行 python -m build
 ▼
[前端 build]  ——读 [build-system]——
 │  1) 建隔离环境，装 requires: setuptools>=61, wheel
 │  2) 导入 build-backend: setuptools.build_meta
 │  3) 调用 backend.build_wheel()   ┐
 │                                  │
 ▼                                  │ 后端干活
[后端 setuptools.build_meta]  ◀────┘
 │  读取 [project] 元数据 + [tool.setuptools...]
 │  收集 src/mygreet/ 源码
 │  写 METADATA / entry_points.txt / RECORD
 │  压缩成 mygreet-0.1.0-py3-none-any.whl
 ▼
[前端 build]  接收 wheel，放到 dist/
一句话概括分工：
- 前端 = 流程控制（建环境、装依赖、调后端、处理产物）
- 后端 = 具体构建逻辑（怎么把源码变成 wheel/sdist）

前端不需要知道后端是 setuptools 还是 hatchling。
后端不需要知道是谁在调用它（pip / build / uv 都行）。
两边通过 pyproject.toml 里的 build-backend + 标准钩子对接。
好处：
换后端（把 setuptools.build_meta 改成 hatchling.build），前端命令不用变。
换前端（pip → uv），后端不用改。
用 requires + 隔离环境，保证构建可复现，不受你本机环境影


后端干活的过程：
一句话就是：后端把pyproject.toml里的声明式配置翻译成包内一个个具体文件。
动作1：读取 [project] 元数据 + [tool.setuptools...]
后端第一件事是把静态配置读进来，映射成它内部需要的东西。映射关系：
| `pyproject.toml` 里的声明 | 后端理解成 |
|---|---|
| `name = "mygreet"` | 包名 + wheel 文件名前缀 |
| `version = "0.1.0"` | 版本号 |
| `description` / `readme` / `authors` / `license` | 写进 `METADATA` 的描述信息 |
| `requires-python = ">=3.9"` | `Requires-Python` |
| `dependencies = []` | `Requires-Dist:`（运行时依赖） |
| `[project.optional-dependencies]` `test = ["pytest"]` | `Provides-Extra: test` + `Requires-Dist: pytest; extra == "test"` |
| `[project.scripts]` `mygreet = "mygreet.cli:main"` | 一条 `console_scripts` 入口点 |
| `[tool.setuptools.packages.find]` `where = ["src"]` | 去 `src/` 找包 |

内部机制：setuptools.build_meta 会把上述值拼成一次经典的 setup(...) 调用再执行。所以你写的 pyproject.toml 本质是"setup.py 的声明式替身"。

动作 2：收集 src/mygreet/ 源码
按 where=["src"] 去扫描：
- 逐个目录检查是否含 __init__.py → 是则算作"包"；
- src/mygreet/ 命中（里面有 __init__.py）→ 记为要打包的包；
- 把该目录下所有 .py 复制到临时目录 build/lib/mygreet/，形成"安装后的最终布局"。
真实中间产物就是之前看到的：
build/lib/mygreet/__init__.py
build/lib/mygreet/cli.py
build/lib/mygreet/core.py
如果 where 配错（比如漏写），这一步就扫不到任何包 → wheel 里没有代码 → 装完 import 失败。这就是那段配置存在的意义。

动作 3：生成元数据文件
后端把这些内容写成若干文本文件，放进包的 xxx.dist-info/（开发构建时则放 xxx.egg-info/）：
METADATA —— 包的身份与依赖（真实输出）：
Metadata-Version: 2.4
Name: mygreet
Version: 0.1.0
Summary: A tiny demo package for learning Python packaging
Author: Demo User
License: MIT
Requires-Python: >=3.9
Provides-Extra: test
Requires-Dist: pytest; extra == "test"

# mygreet ...（这里是 README 的内容，因为 readme="README.md"）
pip show、PyPI 页面、pip install mygreet[test] 判断要不要装 pytest，都是读它。
entry_points.txt —— 安装后要挂的"勾子"（真实输出）：
[console_scripts]
mygreet = mygreet.cli:main
来源就是 [project.scripts]。安装时，前端会据此生成 bin/mygreet 脚本。
WHEEL —— wheel 自身格式说明：
Wheel-Version: 1.0
Root-Is-Purelib: true
Tag: py3-none-any
top_level.txt —— 提供的顶层 import 名：mygreet。

动作 4：生成 RECORD
对包里每个文件算 sha256，列成清单（真实输出节选）：
mygreet/__init__.py,sha256=u-1Efjd-...,89
mygreet/cli.py,sha256=KxK0R2Zv...,311
mygreet/core.py,sha256=zRQnWF5f...,159
mygreet-0.1.0.dist-info/METADATA,sha256=DyWFawwv...,432
...
作用：
- 安装/卸载时按清单精确地放/删文件；
- 校验完整性（哈希对不上说明被改坏或篡改）。

动作 5：打包成 wheel
最后把 build/lib/ 里的代码 + dist-info/ 元数据一起 zip 起来，改后缀得到：
dist/mygreet-0.1.0-py3-none-any.whl



# 手把手：从零构建并打包一个 Python 项目

> 目标：用一个极简的 `mygreet` 包，完整体验 **建项目 → 写代码 → 写配置 → 构建 → 安装 → 验证 → 卸载** 全流程。
> 每一步都说明"在干什么、为什么、产出了什么"。跟着敲一遍即可。

---

## 0. 背景：打包到底是什么

Python 没有编译产物，代码要能分发、能被别的程序 `import`，就必须做成一个"**分发包**"。所谓打包，就是：

```
一堆 .py 源码目录  ──构建工具加工──▶  可安装的包（带元数据 + 入口点）
```

- **构建工具**：`setuptools`（背后执行者） + `build`（命令入口）。
- **产物**：`sdist`（源码包）和 `wheel`（二进制包）。
- **安装**：`pip install <产物>` 把包放进 `site-packages`，并登记元数据。

我们下面就用最现代的方式（`pyproject.toml` + `python -m build`）走一遍。

---

## 1. 环境准备

### 1.1 确认 Python / pip

```bash
python --version      # 需要 3.9+，本机示例 3.12.13
pip --version
```

### 1.2 建一个隔离环境（强烈建议）

不要直接往系统 Python 装东西，用虚拟环境：

```bash
cd /root/cyz/project/python/build_package
python -m venv .venv
source .venv/bin/activate        # 激活后命令行前缀出现 (.venv)
python --version                 # 确认用的是 venv 里的 python
```

> **为什么**：venv 是一个独立的包目录，装/卸都不会污染系统环境，练手最安全。
> 之后所有命令都在激活的 venv 里执行；也可以直接用 `.venv/bin/python` 全路径，免激活。

### 1.3 安装构建工具

```bash
pip install --upgrade pip build
python -m build --version        # 出现 "build x.y.z" 即成功
```

- `build`：官方推荐的构建命令（内部会调用 setuptools）。
- 说明：`python -m venv` 时 pip 已自带；`build` 需要单独装。

---

## 2. 创建项目骨架

一个规范的包目录长这样（**src 布局**，推荐）：

```bash
cd /root/cyz/project/python/build_package
mkdir -p src/mygreet
```

目标结构：

```
build_package/
├── pyproject.toml          # 打包配置（清单）
├── README.md               # 会进入包的长描述
└── src/
    └── mygreet/            # 真正的 Python 包
        ├── __init__.py     # 包的入口，暴露对外接口
        ├── core.py         # 业务逻辑
        └── cli.py          # 命令行入口
```

> **为什么用 `src/` 布局**：把源码和项目根目录隔开，避免"在当前目录能 import、装完却 import 不到"的假象，也强制你安装后再测试。

---

## 3. 写源码（3 个文件）

### 3.1 业务逻辑 `src/mygreet/core.py`

```python
def greet(name: str) -> str:
    if not name:
        name = "world"
    return f"Hello, {name}!"


def shout(name: str) -> str:
    return greet(name).upper()
```

### 3.2 包入口 `src/mygreet/__init__.py`

```python
from mygreet.core import greet, shout

__version__ = "0.1.0"
__all__ = ["greet", "shout"]
```

> `__init__.py` 让 `mygreet` 成为一个"包"；在其中把常用函数 import 出来，用户就能 `from mygreet import greet`。

### 3.3 命令行入口 `src/mygreet/cli.py`

```python
import argparse

from mygreet.core import greet


def main() -> None:
    parser = argparse.ArgumentParser(prog="mygreet", description="Greet someone.")
    parser.add_argument("name", nargs="?", default="world")
    args = parser.parse_args()
    print(greet(args.name))


if __name__ == "__main__":
    main()
```

> `main()` 稍后会通过 `pyproject.toml` 的 `[project.scripts]` 注册成一条 `mygreet` 命令。

### 3.4 先本地跑一下（打包前自测）

在**项目根目录**执行（因为还没安装，靠 `sys.path` 找不到，需临时指定路径）：

```bash
cd /root/cyz/project/python/build_package
PYTHONPATH=src python -c "from mygreet import greet; print(greet('world'))"
# 输出：Hello, world!
```

> 能跑通说明源码没问题，可以进行打包。真正的"安装后验证"放到第 6 步。

---

## 4. 写打包配置 `pyproject.toml`

在项目根目录新建 `pyproject.toml`：

```toml
[build-system]
requires = ["setuptools>=61", "wheel"]
build-backend = "setuptools.build_meta"

[project]
name = "mygreet"
version = "0.1.0"
description = "A tiny demo package for learning Python packaging"
readme = "README.md"
requires-python = ">=3.9"
authors = [{ name = "Demo User" }]
license = { text = "MIT" }
dependencies = []

[project.optional-dependencies]
test = ["pytest"]

[project.scripts]
mygreet = "mygreet.cli:main"

[tool.setuptools.packages.find]
where = ["src"]
```

**逐段解释**：

| 段 | 作用 |
|---|---|
| `[build-system]` | 声明用什么工具构建：setuptools + wheel，入口 `setuptools.build_meta` |
| `[project] name/version` | 包名 + 版本，决定 wheel 文件名 |
| `readme` | 长描述来源（内容会写进 METADATA，pip 页面能看到） |
| `requires-python` | 支持的 Python 版本 |
| `dependencies` | 运行依赖，安装时 pip 会自动一起装（这里为空） |
| `[project.optional-dependencies]` | 可选依赖，例如 `pip install mygreet[test]` 才装 pytest |
| `[project.scripts]` | **入口点**：生成命令 `mygreet`，指向 `mygreet.cli:main` |
| `[tool.setuptools.packages.find] where=["src"]` | 告诉 setuptools 去 `src/` 找包（对应 src 布局） |

> 说明：`pyproject.toml` 是现在的主流写法；它等价于旧的 `setup.py`，但没有命令式代码，更清晰。

同时准备 `README.md`（会被 `readme` 字段引用）：

```markdown
# mygreet

A tiny demo package for learning Python packaging.
```

---

## 5. 构建产物

```bash
cd /root/cyz/project/python/build_package
python -m build
```

**真实输出（结尾）**：

```
Successfully built mygreet-0.1.0.tar.gz and mygreet-0.1.0-py3-none-any.whl
```

### 5.1 产物长什么样

```bash
ls -la dist/
```

| 产物 | 示例 | 作用 |
|---|---|---|
| `mygreet-0.1.0-py3-none-any.whl` | wheel | **二进制包**，已按最终布局打包，安装最快 |
| `mygreet-0.1.0.tar.gz` | sdist | **源码包**，含源码+`pyproject.toml`，安装时现场构建 |

同时会在 `src/` 下出现 `mygreet.egg-info/`，这是构建中间元数据，可删。

### 5.2 wheel 内部结构

```bash
.venv/bin/python -c "import zipfile,glob; print(chr(10).join(zipfile.ZipFile(glob.glob('dist/*.whl')[0]).namelist()))"
```

```
mygreet/__init__.py
mygreet/cli.py
mygreet/core.py
mygreet-0.1.0.dist-info/METADATA          # 名字/版本/依赖/长描述
mygreet-0.1.0.dist-info/WHEEL             # Tag: py3-none-any（纯 Python 跨平台）
mygreet-0.1.0.dist-info/entry_points.txt  # [console_scripts] mygreet = mygreet.cli:main
mygreet-0.1.0.dist-info/top_level.txt     # 顶层 import 名：mygreet
mygreet-0.1.0.dist-info/RECORD            # 每个文件的 sha256，安装/卸载校验用
```

### 5.3 sdist 内部结构

```bash
tar tzf dist/mygreet-0.1.0.tar.gz
```

含 `pyproject.toml`、`README.md`、`src/` 源码、以及自动生成的 `PKG-INFO`、`setup.cfg`。

---

## 6. 安装并验证

### 6.1 安装前：确认没装就 import 不到

```bash
python -c "import mygreet"     # 应报 ModuleNotFoundError
```

### 6.2 安装 wheel

```bash
pip install dist/mygreet-0.1.0-py3-none-any.whl
```

### 6.3 验证四件事

```bash
# 1) 能 import 并调用
python -c "import mygreet; print(mygreet.greet('Alice')); print(mygreet.__version__)"
# Hello, Alice!  /  0.1.0

# 2) 命令行入口生效
mygreet Bob
# Hello, Bob!

# 3) pip 视角元数据
pip show mygreet

# 4) 入口点被环境登记
python -c "import importlib.metadata as m; print([(e.name,e.value) for e in m.entry_points(group='console_scripts') if 'greet' in e.value])"
```

### 6.4 安装后 `site-packages` 里多了什么

```
mygreet/                      # 你的代码
mygreet-0.1.0.dist-info/      # 元数据
  ├── METADATA / WHEEL / entry_points.txt / top_level.txt / RECORD
  ├── INSTALLER               # 由哪个工具安装
  ├── REQUESTED               # 是否用户显式要求安装
  └── direct_url.json         # 从哪里安装的（本地路径 / URL）
bin/mygreet                   # console_scripts 生成的启动脚本
```

---

## 7. 卸载与清理

```bash
pip uninstall -y mygreet

# 清理构建中间物
rm -rf build dist src/*.egg-info
```

> 卸载靠 `RECORD` 精确删除文件；清理后源码目录回到最初的干净状态。

---

## 8. 命令速查

```bash
# 开发模式（改代码即生效，不复制源码；适合调试）
pip install -e .

# 正式构建
python -m build            # sdist + wheel
python -m build --wheel    # 只要 wheel
python -m build --sdist    # 只要 sdist

# 安装 / 更新 / 卸载
pip install dist/xxx.whl
pip install dist/xxx.whl --force-reinstall --no-deps   # 覆盖更新
pip uninstall xxx -y

# 清中间物
rm -rf build dist src/*.egg-info
```

---

## 9. 常见坑

| 现象 | 原因 / 处理 |
|---|---|
| 装完 `import` 报错找不到模块 | 没配 `[tool.setuptools.packages.find] where=["src"]`，包没被打进去 |
| `ModuleNotFoundError` 但明明有 `__init__.py` | 用 src 布局时别在根目录直接 `python xxx.py`；用 `PYTHONPATH=src` 或先安装 |
| wheel 文件名带 `cp312-linux_loongarch64` | 含 C 扩展时会绑定 Python 版本+架构；纯 Python 则是 `py3-none-any` |
| 命令 `mygreet` 找不到 | `[project.scripts]` 写错，或装完没重新开终端（PATH/venv 未生效） |
| 改了代码不生效 | 你装的是 wheel（副本）。调试期改用 `pip install -e .` |
| 构建报缺依赖 | 先 `pip install --upgrade pip build`；有 C 扩展还需对应编译器/环境 |

---

## 10. 一句话总结

**写源码 → 写 `pyproject.toml`（元数据+入口点）→ `python -m build` 出 sdist/wheel → `pip install` 装进环境 → import/命令验证 → `pip uninstall` 卸载。**

这套流程对任何 Python 包都通用；换成你的真实项目，只改包名、源码和依赖，其余步骤不变。


[console_scripts] 是 entry point 里的一个约定组名，专用于"安装后生成命令行命令"。这段的作用是：安装这个包后，生成一个叫 mygreet 的可执行命令，它执行时去调用 mygreet.cli.main()。


1. 两边的含义
[console_scripts]
mygreet = mygreet.cli:main
   │            │     └── 函数（要调用的入口）
   │            └──────── 模块（import mygreet.cli）
   └───────────────────── 命令名（终端里敲的）
- console_scripts：告诉安装器"这是命令行脚本，安装时给我在 bin/ 生成可执行文件"。
- mygreet：你敲的命令。
- mygreet.cli:main：命令实际执行的 模块:函数。
2. 安装时发生什么
pip 读到这行后，会在环境的 bin/ 目录生成一个外壳脚本（真实内容）：
#!/tmp/opencode/pkg-tutorial/.venv/bin/python
import sys
from mygreet.cli import main
if __name__ == '__main__':
    sys.argv[0] = sys.argv[0].removesuffix('.exe')
    sys.exit(main())
于是你就能：
mygreet Alice      # 等价于 python -c "from mygreet.cli import main; main()"
3. 关键理解
- 它不是"函数被自动执行"，而是"生成一个包装脚本，里面 import 并调用你的函数"。
- 它是声明式的：你只写"命令名 = 模块:函数"，生成脚本、放对路径、加执行权限都由 pip 完成。
- 卸载时，pip 按 RECORD 把这个命令脚本一起删掉。
4. 所有 Python CLI 工具都靠它
你环境里真实的例子（同一机制）：
[console_scripts]
vllm    = vllm.entrypoints.cli.main:main     ← 你敲的 vllm 命令
pytest  = _pytest.config:_console_main       ← pytest 命令
black   = black:patched_main
pip install 某个工具后能直接在终端敲它的命令，就是这些 console_scripts 生效的结果。
5. 和其它组名的区别
组名	谁消费、何时	作用
console_scripts	pip，安装时	生成 bin/ 命令
vllm.general_plugins	vLLM，运行时	发现并调用插件注册函数
vllm.platform_plugins	vLLM，运行时	注册硬件平台
格式都是 名字 = 模块:函数，区别只在"组名"决定了谁来读、什么时候读。
一句话总结
[console_scripts] mygreet = mygreet.cli:main = 声明一个命令行入口：安装后 pip 生成 bin/mygreet 脚本，运行它就调用 mygreet.cli.main，让你能像用 pytest、vllm 那样直接敲 mygreet。


## python -m build 和 pip install . 产物不一样
| 对比维度 | `python -m build` | `pip install .` |
|---|---|---|
| 主要目的 | 产出发布物 | 安装进环境 |
| `dist/` | ✅ 默认生成（wheel + sdist） | ❌ 默认不生成 |
| 源码目录 `*.egg-info/` | 可能生成（副作用） | 可能生成（副作用） |
| `build/` | 可能生成（构建产物） | 可能生成（构建副作用） |
| 装进 `site-packages` | ❌ 不安装 | ✅ 安装 |
关键：pip install . 是"现场构建 → 立刻安装到环境"，构建物放在临时目录，用完就没了，所以你的项目里不会出现 dist/。刚才实测印证了这一点。


A) python -m build —— 目的：产出发布物
项目里新增：
dist/
├── mygreet-0.1.0-py3-none-any.whl      # 二进制包
└── mygreet-0.1.0.tar.gz                # 源码包
src/
└── mygreet.egg-info/                   # 构建元数据（中间产物）


B) pip install . —— 目的：安装进环境
项目里新增：
build/                                  # 构建中间目录（有）
src/
└── mygreet.egg-info/                   # 构建元数据（有）
dist/                                   # ← 没有！不产出发布物

site-packages/                          # 装到环境里
├── mygreet/                            # 包本体（代码）
└── mygreet-0.1.0.dist-info/            # 安装后的元数据

生成 mygreet.egg-info/ 的目的是：在构建/安装前，把项目配置解析成一份可供构建工具和安装器读取的元数据快照——用来给 pip 提前判断依赖、给 sdist 提供文件清单、支撑可编辑安装，并让工具不导入代码也能查到包信息。它是 setuptools 的构建中间产物（可编辑安装时需要保留）。

两份 egg-info 内容相同，但一份是你本地的构建中间产物（可删、应 gitignore），另一份是被有意打进 sdist、随源码包分发给别人的内容。就像源码文件在工作和 sdist 里各有一份一样——不是多余，而是"交付需要自包含"。