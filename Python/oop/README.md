# 🐍 Python 面向对象：从会写到会用（手把手课程）

> 不背概念，直接动手。用 10 章、一个贯穿项目，把「类、对象、封装、继承、多态、组合、魔术方法、异常、测试」串成一条完整的工程能力线。

---

## 你会做出什么

完成课程后，你会亲手写出一个可运行、可测试的**图书借阅系统**：

- 用类建模图书、会员、借阅记录和图书馆
- 用封装保证库存永远不会变成负数
- 用继承和多态统一处理纸质书、电子书
- 用组合把对象搭成一个系统，而不是写成一坨函数
- 用魔术方法让对象支持 `print`、`len`、`for`、`in`
- 用类方法、静态方法和 `dataclass` 写出更简洁的模型
- 用自定义异常表达业务失败，而不是到处返回 `None`
- 用 `unittest` 验证借书、还书、逾期、借阅上限
- 能识别常见的面向对象坏味道，并知道怎么重构

项目只使用 Python 标准库，**不需要安装任何第三方包**。

---

## 适合谁

- 已经会写变量、`if`、`for`、函数、列表和字典
- 能看懂 `def`、参数、返回值，但一看到 `self`、`__init__` 就发怵
- 抄过别人的类，却说不清什么时候该用类、什么时候该用函数
- 想从「语法会了」走到「能设计一个小系统」

不需要：

- 学过 Java / C++ 的面向对象
- 懂设计模式
- 懂 Web 框架

---

## 学习路线

| 章节 | 主题 | 你会得到 | 建议时间 |
| :---: | :--- | :--- | :---: |
| [00](./chapters/00_mental_model.md) | 心智模型 | 明白对象到底解决什么问题 | 30 分钟 |
| [01](./chapters/01_class_and_instance.md) | 类与实例 | 第一个真正可用的 `Book` 类 | 60 分钟 |
| [02](./chapters/02_encapsulation.md) | 封装 | 带校验和只读属性的库存模型 | 60 分钟 |
| [03](./chapters/03_inheritance.md) | 继承与多态 | 纸质书 / 电子书的统一接口 | 75 分钟 |
| [04](./chapters/04_composition.md) | 组合 | `Library` 把对象组织起来 | 75 分钟 |
| [05](./chapters/05_magic_methods.md) | 魔术方法 | 像内置类型一样自然的对象 | 60 分钟 |
| [06](./chapters/06_classmethod_dataclass.md) | 类方法 / dataclass | 更简洁、更专业的模型代码 | 60 分钟 |
| [07](./chapters/07_errors_protocols.md) | 异常与协议 | 清晰的失败边界和可替换依赖 | 60 分钟 |
| [08](./chapters/08_project.md) | 综合实战 | 完整图书借阅系统 | 120 分钟 |
| [09](./chapters/09_testing_next.md) | 测试与进阶 | 测试、重构、避坑、下一步 | 60 分钟 |

> 建议按顺序学。每章都包含「先运行 → 再拆解 → 动手改 → 做练习」四步，**不要只读不跑**。

---

## 课程项目长什么样

我们不会东一榔头西一棒子地写零散例子，而是让同一个项目逐步长大：

```text
第 1-2 章   Book：图书本身
第 3 章     PaperBook / EBook：不同类型的书
第 4 章     Member / Loan / Library：借阅关系
第 5 章     给这些对象加上 Python 风格的魔术方法
第 6 章     用 dataclass 和类方法重构模型
第 7 章     用自定义异常和 Protocol 划清边界
第 8 章     组装成完整、可运行、可测试的项目
第 9 章     补测试、做重构、识别常见坑
```

最终的对象关系：

```text
Library  1 ─── * Book
   │
   └── * Member  1 ─── * Loan  * ─── 1 Book
```

翻译成人话：

- 一个图书馆管理很多书和很多会员
- 一个会员可以有多条借阅记录
- 一条借阅记录对应一本书
- `Library` 负责协调，`Book` 负责库存，`Member` 负责借阅额度，`Loan` 负责期限

这就是「把职责分给对象」，也是本课程真正想教的东西。

---

## 环境准备

要求：**Python 3.10+**（代码用到了 `X | None` 这种类型写法）。

```bash
python --version
```

如果系统里没有可用的 `python` 命令，但安装了 [uv](https://docs.astral.sh/uv/)，可以用：

```bash
uv run python --version
```

进入课程目录：

```bash
cd Python/oop
```

不需要虚拟环境，也不需要 `pip install` 任何东西。后文的 `python` 命令都可以替换成 `uv run python`。

### 运行章节示例

所有章节示例都在 `examples/` 下，统一用模块方式运行（避免相对导入问题）：

```bash
python -m examples.ch01_book
python -m examples.ch02_book
python -m examples.ch03_books
python -m examples.ch04_library
python -m examples.ch05_magic
python -m examples.ch06_models
python -m examples.ch07_errors
```

### 运行最终项目

```bash
cd project
python demo.py
python -m unittest -v
```

Windows 终端如果中文乱码，先执行：

```bat
chcp 65001
```

或设置：

```bat
set PYTHONIOENCODING=utf-8
```

---

## 目录结构

```text
oop/
├── README.md                  # 本文件
├── chapters/                  # 00-09 章教程
│   ├── 00_mental_model.md
│   ├── 01_class_and_instance.md
│   ├── 02_encapsulation.md
│   ├── 03_inheritance.md
│   ├── 04_composition.md
│   ├── 05_magic_methods.md
│   ├── 06_classmethod_dataclass.md
│   ├── 07_errors_protocols.md
│   ├── 08_project.md
│   └── 09_testing_next.md
├── examples/                  # 每章的完整可运行代码
│   ├── ch01_book.py
│   ├── ch02_book.py
│   ├── ch03_books.py
│   ├── ch04_library.py
│   ├── ch05_magic.py
│   ├── ch06_models.py
│   └── ch07_errors.py
└── project/                   # 最终项目
    ├── library_system/
    │   ├── __init__.py
    │   ├── errors.py
    │   ├── models.py
    │   └── library.py
    ├── demo.py
    └── test_library.py
```

---

## 每章怎么学

每章都按同一个节奏设计：

1. **先运行**：把示例跑起来，看输出。
2. **再拆解**：逐段解释代码，回答「为什么这么写」。
3. **动手改**：课程会给出一个明确的小改动，让你立刻验证理解。
4. **做练习**：难度略高，要求你自己设计一点东西。
5. **过检查点**：用几个问题确认自己真的会了，再进入下一章。

一个很重要的学习方法：

> **先预测输出，再运行。**
>
> 看到一段代码时，先在心里（或纸上）说出它会打印什么。运行结果和预测不一致的地方，就是最值得停下来弄懂的地方。

---

## 课程约定

### 名称约定

| 写法 | 含义 |
| :--- | :--- |
| `self` | 实例方法的第一个参数，指向当前对象 |
| `_name` | 内部属性，约定「不要从外部直接改」 |
| `__name` | 名称改写，避免子类意外覆盖（本课程少用） |
| `__init__` | 初始化方法，对象创建后自动调用 |
| `@property` | 把方法伪装成属性 |
| `@classmethod` | 第一个参数是类本身 `cls` |
| `@staticmethod` | 不接收 `self` / `cls` 的普通函数 |
| `ABC` | 抽象基类，用来定义「必须实现什么」 |
| `Protocol` | 结构化接口，只看「有没有这个方法」 |

### 代码原则

1. **小步前进。** 每章只加一个概念，不一次性堆完。
2. **先能跑，再优雅。** 不要为了「设计」把自己卡死。
3. **让非法状态无法出现。** 能校验的，在对象创建或方法入口校验。
4. **优先组合，谨慎继承。** 继承表达「是一个」，组合表达「有一个」。
5. **异常用于异常情况。** 不要用异常做普通流程控制，也不要默默返回 `None` 掩盖错误。

---

## 学完后的下一步

完成课程后，你可以继续：

- 给项目加 JSON / SQLite 持久化
- 把借阅规则抽象成策略对象（学生会员、教师会员不同借期）
- 用 `pytest` 重写测试，体验 fixture 和参数化
- 学习 `typing.Protocol`、`abc`、`dataclasses` 的更多用法
- 阅读一个真实项目的模型层，尝试画出类关系图
- 学习 SOLID 原则和常用设计模式，但**先写代码再看模式**

---

## 一句话总结

**面向对象不是「多写几个 class」，而是把数据、规则和行为放进合适的对象里，再让对象通过清晰的接口协作。**

从 [第 00 章](./chapters/00_mental_model.md) 开始吧。