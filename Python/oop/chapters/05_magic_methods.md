# 第 05 章：魔术方法——让对象像内置类型一样自然

> 本章目标：让你的对象支持 `print()`、`==`、`len()`、`for`、`in` 和 `with`，写出「长得像 Python」的类。

---

## 5.1 先运行

```bash
python -m examples.ch05_magic
```

输出（`Timer` 的秒数每次略有不同）：

```text
《Python 编程》
Book(isbn='978-7-111-40701-0', title='Python 编程')
True
2
Library(books=2)
2
True
《Python 编程》
《算法导论》
求和: 0.021s
500000500000
```

完整代码在 [`examples/ch05_magic.py`](../examples/ch05_magic.py)。

---

## 5.2 什么是魔术方法

魔术方法（magic method / dunder method）是名字前后各有两个下划线的方法，例如：

```python
__init__
__str__
__repr__
__eq__
__len__
__iter__
```

它们不是给你直接调用的，而是 Python 在特定语法下自动调用：

| 你写的代码 | Python 实际调用 |
| :--- | :--- |
| `print(obj)` | `obj.__str__()` |
| `repr(obj)` | `obj.__repr__()` |
| `obj1 == obj2` | `obj1.__eq__(obj2)` |
| `len(obj)` | `obj.__len__()` |
| `for x in obj` | `obj.__iter__()` |
| `x in obj` | `obj.__contains__(x)` |
| `with obj:` | `obj.__enter__()` / `obj.__exit__()` |

实现这些方法，你的对象就能自然地融入 Python 的语法，而不是让调用方记住一堆 `get_xxx()`。

---

## 5.3 `__str__` vs `__repr__`

```python
class Book:
    def __str__(self) -> str:
        return f"《{self.title}》"

    def __repr__(self) -> str:
        return f"Book(isbn={self.isbn!r}, title={self.title!r})"
```

```python
book = Book("978-7-111-40701-0", "Python 编程")
print(book)          # 《Python 编程》
print(repr(book))    # Book(isbn='978-7-111-40701-0', title='Python 编程')
```

两者的定位不同：

| 方法 | 给谁看 | 目标 |
| :--- | :--- | :--- |
| `__str__` | 最终用户 | 可读、友好 |
| `__repr__` | 开发者 / 调试 | 精确、尽量能重建对象 |

经验规则：

- `__repr__` 是「官方表示」，应该尽量无歧义
- `__str__` 是「人类友好表示」，可以更漂亮
- 如果只实现一个，优先实现 `__repr__`
- 因为 `print()` 找不到 `__str__` 时会退回 `__repr__`

### 容器里的对象用 `repr`

```python
books = [book]
print(books)
```

输出是 `[Book(isbn='...', title='...')]`，不是 `[《Python 编程》]`。因为列表的 `__str__` 会调用元素的 `__repr__`。

这也是为什么调试时 `repr` 更重要：你在列表、字典、日志里看到的，通常是 `repr`。

### `!r` 是什么

```python
f"{value!r}"
```

等价于 `repr(value)`。字符串会带上引号，调试时能看出类型：

```python
print(f"{'abc'}")    # abc
print(f"{'abc'!r}")  # 'abc'
```

---

## 5.4 `__eq__`：定义「相等」是什么意思

默认的 `==` 比较的是对象身份：

```python
b1 = Book("978-7-111-40701-0", "Python 编程")
b2 = Book("978-7-111-40701-0", "Python 编程")
print(b1 == b2)   # False，因为不是同一个对象
```

但对图书来说，ISBN 相同就应该视为同一本书：

```python
def __eq__(self, other: object) -> bool:
    if not isinstance(other, Book):
        return NotImplemented
    return self.isbn == other.isbn
```

```python
print(b1 == b2)   # True
```

### 为什么返回 `NotImplemented`，不是 `False`

当 `other` 不是 `Book` 时，返回 `NotImplemented` 告诉 Python：

> 我不知道怎么和这个类型比较，你问问对方，或者用默认规则。

如果直接返回 `False`，会阻止 Python 尝试对方的 `__eq__`，可能得到错误结果。

`NotImplemented` 是一个特殊常量，不是异常，也不是 `NotImplementedError`。

### 定义了 `__eq__`，`__hash__` 会消失

这是 Python 的一个陷阱：

```python
class Book:
    def __eq__(self, other: object) -> bool:
        ...
    # 没有定义 __hash__
```

此时 `Book` 实例不可哈希，不能放进 `set`，也不能作为 `dict` 的键：

```python
{b1, b2}   # TypeError: unhashable type: 'Book'
```

因为「相等」和「哈希」必须保持一致：

- 如果 `a == b`，那么 `hash(a)` 必须等于 `hash(b)`
- 否则 `set` 和 `dict` 会出错

所以定义了 `__eq__`，通常也要定义 `__hash__`：

```python
def __hash__(self) -> int:
    return hash(self.isbn)
```

本章的 `Book` 以 ISBN 作为身份，因此用 ISBN 计算哈希。

### 可变对象不要做哈希键

如果对象创建后 ISBN 会变，那么它作为 `set` 元素或 `dict` 键时会「消失」。本章的 `isbn` 视为不可变，所以安全。

---

## 5.5 `__len__`、`__iter__`、`__contains__`

让 `Library` 像一个集合：

```python
class Library:
    def __len__(self) -> int:
        return len(self._books)

    def __iter__(self) -> Iterator[Book]:
        return iter(self._books.values())

    def __contains__(self, isbn: object) -> bool:
        return isinstance(isbn, str) and isbn in self._books
```

于是可以：

```python
library = Library()
library.add(book)

print(len(library))                  # 2
print("978-7-111-40701-0" in library) # True
for book in library:
    print(book)
```

### `__len__` 还影响布尔值

```python
if library:
    print("图书馆不是空的")
```

Python 找不到 `__bool__` 时，会看 `__len__`：长度为 0 就是 `False`，否则 `True`。

### `__iter__` 返回什么

它应该返回一个迭代器。最简单的是返回内部容器的迭代器：

```python
return iter(self._books.values())
```

不要写成：

```python
return self._books.values()   # 也行，但显式 iter 更清楚
```

更不要写：

```python
for book in self._books.values():
    yield book
```

两种都能工作，但 `iter(...)` 更直接。

### 为什么不直接暴露 `_books`

因为一旦调用方拿到内部字典，就能随意增删：

```python
library._books.clear()   # 绕过所有规则
```

`__iter__` 给的是「只读遍历」能力，不暴露修改入口。这就是魔术方法版的封装。

### `__contains__` 的参数类型

`x in obj` 里的 `x` 可以是任何类型，所以参数通常写成 `object`，在里面做类型检查：

```python
def __contains__(self, isbn: object) -> bool:
    return isinstance(isbn, str) and isbn in self._books
```

如果直接写 `isbn in self._books`，传一个列表会抛 `TypeError` 吗？不会，字典会尝试哈希列表，结果抛异常。先检查类型更稳。

---

## 5.6 `__getitem__`：支持下标访问

```python
class Shelf:
    def __init__(self) -> None:
        self._books: list[Book] = []

    def add(self, book: Book) -> None:
        self._books.append(book)

    def __getitem__(self, index: int) -> Book:
        return self._books[index]
```

```python
shelf = Shelf()
shelf.add(book)
print(shelf[0])
```

只要实现了 `__getitem__`，对象就自动支持：

- `shelf[0]`
- `shelf[-1]`
- 切片 `shelf[1:3]`（如果 `index` 是 `slice`，需要自己处理）
- 甚至 `for x in shelf`（Python 会从索引 0 开始迭代，直到 `IndexError`）

不过，**显式实现 `__iter__` 通常更清晰**，不要依赖 `__getitem__` 的隐式迭代。

---

## 5.7 上下文管理器：`with`

```python
class Timer:
    def __init__(self, label: str) -> None:
        self.label = label
        self._start = 0.0

    def __enter__(self) -> Timer:
        self._start = perf_counter()
        return self

    def __exit__(self, exc_type, exc_value, traceback) -> None:
        elapsed = perf_counter() - self._start
        print(f"{self.label}: {elapsed:.3f}s")
```

```python
with Timer("求和"):
    total = sum(range(1_000_001))
```

执行流程：

```text
1. 创建 Timer 实例
2. 调用 __enter__()，返回值绑定到 as 后面的变量（这里没用 as）
3. 执行 with 代码块
4. 无论是否异常，都调用 __exit__(...)
```

`__exit__` 的返回值决定异常是否被吞掉：

- 返回 `None` / `False`：异常继续传播
- 返回 `True`：异常被抑制

本章的 `Timer` 返回 `None`，所以异常会正常抛出，但计时仍会执行。这正是 `with` 的价值：**清理逻辑一定会运行**。

### 不要滥用上下文管理器

`with` 适合「有开始和结束、结束必须执行」的场景：

- 打开/关闭文件
- 获取/释放锁
- 开始/结束事务
- 计时
- 临时修改配置

如果只是普通计算，不需要为了炫技套一个 `with`。

---

## 5.8 `__call__`：让对象像函数一样调用

```python
class Multiplier:
    def __init__(self, factor: int) -> None:
        self.factor = factor

    def __call__(self, value: int) -> int:
        return value * self.factor

double = Multiplier(2)
print(double(10))   # 20
```

`double` 是对象，但可以像函数一样调用。适合「带状态的函数」，例如策略对象、缓存函数。

初学阶段知道即可，不要把所有对象都写成可调用的。

---

## 5.9 动手改

在 `examples/ch05_magic.py` 中：

1. 给 `Library` 增加 `__getitem__(self, isbn: str) -> Book`，找不到时抛 `KeyError`。
2. 给 `Book` 增加 `__lt__`，按 `title` 排序。
3. 用 `sorted([...])` 验证排序结果。

参考实现：

```python
def __getitem__(self, isbn: str) -> Book:
    return self._books[isbn]

def __lt__(self, other: Book) -> bool:
    if not isinstance(other, Book):
        return NotImplemented
    return self.title < other.title
```

---

## 5.10 常见坑

### 坑 1：定义了 `__eq__` 忘记 `__hash__`

对象突然不能放进 `set`。如果你希望对象可哈希，补上 `__hash__`；如果对象可变且不该做键，就明确让它不可哈希。

### 坑 2：`__hash__` 用了可变字段

```python
def __hash__(self) -> int:
    return hash(self.title)   # title 改了，哈希就变了
```

对象放进 `set` 后修改字段，会导致它再也找不到。用不可变字段（如 ISBN）做哈希。

### 坑 3：`__repr__` 返回不合法或过长内容

`__repr__` 应该简洁、稳定。不要在里面查询数据库、读文件或打印一大坨内容。

### 坑 4：`__len__` 返回负数或非整数

`len()` 要求非负整数，否则抛 `TypeError`。

### 坑 5：`__contains__` 里递归调用 `in`

```python
def __contains__(self, x):
    return x in self   # 无限递归
```

应该检查内部容器：

```python
return x in self._items
```

### 坑 6：以为 `__str__` 能控制容器输出

列表、字典打印元素时用的是 `__repr__`。想控制调试输出，重点写 `__repr__`。

---

## 5.11 本章练习

### 练习 A：`Shelf`

实现 `Shelf`：

- 内部列表 `_books`
- `add(book)`
- `__len__`
- `__iter__`
- `__getitem__`，支持索引和切片
- `__contains__`，判断某本 `Book` 是否在书架上

提示：切片时 `self._books[index]` 会返回列表，类型标注可以写 `Book | list[Book]`。

### 练习 B：`Loan` 的可读表示

给 `Loan` 实现 `__repr__`，输出：

```text
Loan(book='Python 编程', member='小明', due=2026-11-09, active=True)
```

要求 `active` 根据 `returned_on` 动态计算。

### 练习 C：思考

为什么 `Book` 用 ISBN 做 `__eq__`，而不是用 `title`？

如果两本书 ISBN 相同、书名不同（比如不同版次），它们应该相等吗？先确定业务规则，再决定代码。

---

## 5.12 检查点

1. `__str__` 和 `__repr__` 分别给谁看？只写一个时优先写哪个？
2. 定义了 `__eq__` 后，为什么 `__hash__` 会变成 `None`？
3. `len(obj)`、`for x in obj`、`x in obj` 分别调用哪个魔术方法？
4. `with` 语句执行了哪些方法？`__exit__` 返回 `True` 意味着什么？
5. 为什么 `__iter__` 比直接暴露内部列表更好？

如果第 1、2、3 题能说清，你已经能让对象「融入 Python」了。

---

[← 上一章：组合](./04_composition.md) | [下一章：类方法与 dataclass →](./06_classmethod_dataclass.md)