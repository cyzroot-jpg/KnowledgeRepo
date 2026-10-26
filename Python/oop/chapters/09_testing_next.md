# 第 09 章：测试、重构与进阶

> 本章目标：给对象加上「安全网」，识别常见的坏味道，并知道下一步该学什么。

---

## 9.1 为什么面向对象需要测试

对象有状态，状态会变化，方法之间会互相影响。一个看似简单的修改，可能破坏很远处的行为。

测试的价值不是「证明代码没错」，而是：

- 改代码时，能快速知道有没有弄坏已有功能
- 把业务规则写成可执行的文档
- 逼你把对象设计成可独立创建、可独立验证的样子

如果一个类很难测试，通常说明它依赖了太多东西。

---

## 9.2 一个测试的完整结构

以项目里的测试为例：

```python
def test_return_restores_available(self) -> None:
    self.library.borrow(self.book.isbn, self.member.member_id, self.today)
    loan = self.library.return_book(
        self.book.isbn,
        self.member.member_id,
        self.today,
    )

    self.assertEqual(self.book.available, 2)
    self.assertFalse(loan.is_active)
    self.assertEqual(self.member.loan_count, 0)
```

它遵循 **Arrange - Act - Assert**：

```text
Arrange（准备）：借出一本书
Act（执行）    ：归还
Assert（断言） ：库存恢复、记录关闭、会员借阅数归零
```

写测试时，先把这三段分开，测试会清楚很多。

---

## 9.3 测行为，不测实现

### 好的测试

```python
def test_borrow_decreases_available(self) -> None:
    self.library.borrow(self.book.isbn, self.member.member_id, self.today)
    self.assertEqual(self.book.available, 1)
```

它只关心「借书后可用库存减一」这个**行为**。

### 脆弱的测试

```python
def test_borrow_decreases_available(self) -> None:
    self.library.borrow(self.book.isbn, self.member.member_id, self.today)
    self.assertEqual(self.book._available, 1)
```

它依赖内部字段名 `_available`。哪天你把内部实现改成 `_stock`，测试就挂了，但功能其实没变。

原则：

> **测试公开行为，不测试私有实现。**

例外：某些关键不变量确实只能通过内部字段验证，但优先寻找公开接口。

---

## 9.4 测试边界和异常

不要只测「一切正常」。至少覆盖：

- 正常路径
- 边界值（库存 0、借阅数刚好等于上限、到期日当天）
- 非法输入（空 ISBN、负数库存、不存在的会员）
- 重复操作（重复借、重复还、重复添加）
- 状态转换（借出 → 归还 → 再借）

项目里的测试已经覆盖了不少：

```python
def test_overdue(self) -> None:
    loan = self.library.borrow(self.book.isbn, self.member.member_id, self.today)

    self.assertFalse(loan.is_overdue(self.today + timedelta(days=14)))
    self.assertTrue(loan.is_overdue(self.today + timedelta(days=15)))

    self.library.return_book(
        self.book.isbn,
        self.member.member_id,
        self.today + timedelta(days=16),
    )
    self.assertFalse(loan.is_overdue(self.today + timedelta(days=20)))
```

注意它测了三个时间点：

- 到期日当天：不逾期（业务约定）
- 到期次日：逾期
- 归还后：即使过了很久，也不再算逾期

**边界值是 bug 的高发区。**

---

## 9.5 测试替身：用 `MemoryNotifier`

项目的 `Library` 不直接依赖 `ConsoleNotifier`，所以测试时可以传入一个记录消息的对象：

```python
class MemoryNotifier:
    def __init__(self) -> None:
        self.messages: list[str] = []

    def notify(self, message: str) -> None:
        self.messages.append(message)


def test_borrow_notifies(self) -> None:
    notifier = MemoryNotifier()
    library = Library(notifier)
    ...
    assert notifier.messages == ["小明 借了《Python 编程》"]
```

这就是依赖注入带来的可测试性：

- 不需要真的发邮件
- 不需要捕获标准输出
- 可以精确断言通知内容

`MemoryNotifier` 就是测试替身（test double）的一种。它不继承 `Notifier`，但满足协议。

---

## 9.6 从 `unittest` 到 `pytest`

项目的测试用标准库 `unittest`，因为它不需要安装任何东西：

```bash
python -m unittest -v
```

如果你以后用 `pytest`，同样的测试可以写得更短：

```python
def test_borrow_decreases_available():
    library = Library()
    book = Book("978-7-111-40701-0", "Python 编程", "张三", total_copies=2)
    member = Member("M001", "小明")
    library.add_book(book)
    library.register_member(member)

    library.borrow(book.isbn, member.member_id, date(2026, 1, 1))

    assert book.available == 1
```

`pytest` 的优势：

- 普通 `assert` 就能断言
- fixture 管理测试数据
- 参数化测试
- 更友好的失败输出
- 插件生态丰富

但**先学会写清楚的测试，再换工具**。工具不会替你设计测试用例。

---

## 9.7 什么时候该重构

重构不是「把代码改好看」，而是**在不改变外部行为的前提下改善内部结构**。

常见信号：

| 信号 | 可能的问题 | 重构方向 |
| :--- | :--- | :--- |
| 一个方法很长，注释比代码多 | 职责太多 | 提取方法 |
| 一个类有几十个方法，什么都管 | 类太大 | 拆类 / 提取协作对象 |
| 到处 `if isinstance(...)` | 用条件代替多态 | 把行为放进子类或用协议 |
| 修改一个类，牵连很多文件 | 耦合太紧 | 降低依赖、引入接口 |
| 大量重复代码 | 逻辑散落 | 提取公共方法 / 组合 |
| 子类越来越多，父类越来越重 | 继承滥用 | 改为组合 |
| 参数列表很长，经常传 `None` | 职责不清 | 引入参数对象 / 配置对象 |
| 测试很难写 | 依赖太多 | 依赖注入、拆职责 |

一个实用判断：

> **如果每次加需求都要改很多不相关的代码，说明边界出了问题。**

---

## 9.8 几种常用重构手法

### 1. 提取方法（Extract Method）

```python
# 重构前
def borrow(self, isbn, member_id, today=None):
    today = today or date.today()
    book = self._books.get(isbn)
    if book is None:
        raise BookNotFound(...)
    member = self._members.get(member_id)
    if member is None:
        raise MemberNotFound(...)
    if not member.can_borrow:
        raise LoanLimitReached(...)
    ...
```

```python
# 重构后
def borrow(self, isbn, member_id, today=None):
    today = today or date.today()
    book = self._require_book(isbn)
    member = self._require_member(member_id)
    self._ensure_can_borrow(member)
    ...
```

方法变短，`_require_book` 也能被 `return_book` 复用。

### 2. 以多态替代条件

```python
# 重构前
if book.type == "paper":
    days = 14
elif book.type == "ebook":
    days = 7
elif book.type == "reference":
    days = 3
```

```python
# 重构后
days = book.loan_days
```

把差异放进对象，调用方只依赖统一接口。

### 3. 以组合替代继承

```python
# 继承：TeacherMember 是一种 Member，但借期规则变化很多
class TeacherMember(Member):
    @property
    def loan_days(self) -> int:
        return 30
```

```python
# 组合：会员持有一个借阅策略
class Member:
    def __init__(self, ..., policy: LoanPolicy) -> None:
        self.policy = policy

class StudentPolicy:
    def loan_days(self) -> int:
        return 14

class TeacherPolicy:
    def loan_days(self) -> int:
        return 30
```

当变化的是「规则」而不是「类型」时，组合通常更灵活。

### 4. 引入值对象

不要把「ISBN」「金额」「日期范围」当成裸字符串或裸数字到处传：

```python
@dataclass(frozen=True)
class Isbn:
    value: str

    def __post_init__(self) -> None:
        if not self.value.strip():
            raise ValueError("ISBN 不能为空")
```

值对象的好处：

- 校验集中
- 不会把「ISBN」和「书名」搞混
- 可以安全地作为 `dict` 键
- 行为可以挂在它身上（格式化、校验）

### 5. 依赖注入

```python
# 难测试
class Library:
    def __init__(self) -> None:
        self.notifier = EmailNotifier()

# 可替换
class Library:
    def __init__(self, notifier: Notifier | None = None) -> None:
        self.notifier = notifier
```

依赖注入不是框架专属，普通 Python 代码就能用。

---

## 9.9 常见坑总表

### 1. `self` 相关

| 现象 | 原因 | 修复 |
| :--- | :--- | :--- |
| `AttributeError: no attribute 'x'` | 写成了 `x = x` | 改成 `self.x = x` |
| 方法调用多了一个参数 | 定义方法漏了 `self` | 第一个参数加 `self` |
| 子类实例没有父类属性 | 没调用 `super().__init__` | 补上 |

### 2. 可变默认值

```python
class Member:
    def __init__(self, loans: list[str] = []) -> None:   # 所有实例共享
        self.loans = loans
```

修复：

```python
def __init__(self, loans: list[str] | None = None) -> None:
    self.loans = loans if loans is not None else []
```

`dataclass` 用 `field(default_factory=list)`。

### 3. `is` 和 `==`

```python
a = [1, 2]
b = [1, 2]
a == b   # True，值相等
a is b   # False，不是同一个对象
```

- `==` 比较值（调用 `__eq__`）
- `is` 比较身份（是不是同一个对象）

判断 `None` 用 `is None`：

```python
if value is None:
    ...
```

不要用 `if value == None`。

### 4. 可变对象做哈希键

```python
book.title = "新书名"
# 如果 __hash__ 基于 title，book 在 set 里就找不到了
```

用不可变字段做哈希，或者不要让可变对象可哈希。

### 5. property 递归

```python
@property
def available(self):
    return self.available   # 无限递归
```

返回内部字段 `self._available`。

### 6. 继承层级过深

```text
Book -> PaperBook -> ChinesePaperBook -> ChinesePaperBookV2
```

每加一层，理解成本上升。优先考虑组合、协议、策略对象。

### 7. 在 `__init__` 里做太多事

```python
def __init__(self) -> None:
    self.books = load_from_database()
    self.members = load_from_api()
    self.start_background_thread()
```

对象创建应该轻量。重活交给显式方法，或者依赖注入进来。

### 8. 循环导入

```text
models.py 导入 library.py
library.py 导入 models.py
```

修复方向：

- 把共用的异常/类型移到独立模块
- 用 `from __future__ import annotations` 延迟注解求值
- 重新检查职责边界，通常循环导入意味着分层有问题

### 9. 过度设计

为了一个 50 行的脚本引入：

- 抽象工厂
- 策略模式
- 依赖注入容器
- 三层架构

这不是专业，是负担。**先让代码清楚，再在变化出现时抽象。**

### 10. 用 `type()` 而不是 `isinstance()`

```python
if type(book) is Book:      # 不包含子类
    ...

if isinstance(book, Book):  # 包含子类
    ...
```

大多数场景用 `isinstance`。但如果你发现自己在大量 `isinstance`，先想想是不是该用多态。

---

## 9.10 关于 MRO 和 `super()` 的补充

单继承时，`super()` 很清楚。多继承时，Python 用 C3 线性化算法确定方法查找顺序：

```python
class A:
    def hello(self) -> str:
        return "A"

class B(A):
    def hello(self) -> str:
        return "B" + super().hello()

class C(A):
    def hello(self) -> str:
        return "C" + super().hello()

class D(B, C):
    pass

print(D().hello())    # BCA
print(D.__mro__)
# (D, B, C, A, object)
```

`super()` 不是「调用父类」，而是「调用 MRO 中的下一个类」。理解这一点，才能看懂协作式多继承。

不过，**初学阶段不要用多继承**。绝大多数业务代码用单继承 + 组合 + Protocol 就够了。

---

## 9.11 下一步学什么

### 1. 类型标注与静态检查

- `typing`：`Protocol`、`Generic`、`TypeVar`、`Literal`
- `mypy` / `pyright`：在运行前发现类型错误
- 给公共 API 加类型标注，内部代码可以适度宽松

### 2. 数据模型

- `dataclasses` 的更多用法：`frozen`、`slots`、`kw_only`
- `attrs` / `pydantic`：更强大的校验和序列化
- 值对象与实体（Entity）的区别

### 3. 设计原则

- SOLID
- 依赖倒置
- 接口隔离
- 组合优于继承

不要背定义，遇到真实的重构场景再回来看。

### 4. 设计模式

先掌握这些最常见的：

- 策略（Strategy）
- 工厂（Factory）
- 适配器（Adapter）
- 观察者（Observer）
- 模板方法（Template Method）

重点不是记住 UML，而是识别「这里的变化点，应该被封装成对象」。

### 5. 阅读真实项目

挑一个你熟悉的库，观察它的：

- 模型层怎么划分
- 异常体系怎么设计
- 依赖怎么注入
- 测试怎么组织
- 哪些地方用了继承，哪些地方用了组合

推荐从你正在用的库开始，而不是一上来读框架源码。

### 6. 更深入的语言机制

- `__slots__`：减少实例内存
- descriptor：`property` 的底层机制
- 元类：类的类
- 生成器与迭代器协议
- `contextlib`：更简洁的上下文管理器

这些不是必须，但会让你更懂 Python。

---

## 9.12 最终自查清单

### 设计

- [ ] 每个类能用一句话说清职责
- [ ] 没有为了复用而强行继承
- [ ] 对象之间通过公开方法协作，不直接改内部字段
- [ ] 非法状态无法通过公开 API 制造
- [ ] 失败有明确的异常类型
- [ ] 依赖可以通过构造函数或参数替换

### 代码

- [ ] 没有可变类属性 / 可变默认参数
- [ ] `self` 使用正确
- [ ] 定义了 `__eq__` 时考虑过 `__hash__`
- [ ] `None` 用 `is None` 判断
- [ ] property 没有递归
- [ ] 没有循环导入

### 测试

- [ ] 正常路径有测试
- [ ] 边界值有测试
- [ ] 异常路径有测试
- [ ] 测试不依赖真实时间 / 网络 / 文件系统
- [ ] 测试断言的是行为，不是内部字段

### 可读性

- [ ] 命名表达意图，不用 `data`、`obj`、`temp` 这类空泛名字
- [ ] 方法长度适中，复杂逻辑有拆分
- [ ] 注释解释「为什么」，而不是复述「做了什么」
- [ ] 没有为了模式而模式

---

## 9.13 课程回顾

从第 00 章到这里，你完成了：

```text
过程式字典
  → 类与实例
  → 封装与不变量
  → 继承与多态
  → 组合与职责分配
  → 魔术方法与 Python 风格
  → dataclass 与工厂方法
  → 自定义异常与 Protocol
  → 完整项目
  → 测试与重构
```

你现在应该能做到：

- 看到一个需求，先找名词和动词，而不是急着写函数
- 判断一个动作该放在哪个对象上
- 用封装保护不变量
- 用继承表达稳定的 is-a，用组合应对变化
- 用异常表达失败，用协议解耦依赖
- 为一个类写独立、可重复的测试
- 识别「类太大、继承太深、条件太多、耦合太紧」这些信号

---

## 9.14 最后的话

面向对象不是「写很多 class」，也不是「把每个函数都塞进类里」。

它真正解决的问题是：

> **当系统变复杂时，如何让每一部分只关心自己该关心的事，并且能独立变化。**

如果有一天你发现：

- 这个类只有一个方法
- 这个继承层级只有一层，而且永远不会扩展
- 这个抽象接口只有一个实现

那就大胆地删掉它。**简单、清楚、能改**，比「看起来像设计模式」重要得多。

---

[← 上一章：综合实战](./08_project.md) | [返回课程首页](../README.md)