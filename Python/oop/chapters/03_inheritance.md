# 第 03 章：继承与多态——同一接口，不同行为

> 本章目标：用抽象基类定义「一本书应该能做什么」，再让纸质书、电子书、工具书各自实现，最后用统一的方式处理它们。

---

## 3.1 先看需求

图书馆里的书不只有一种：

- 纸质书：可借 14 天，有页数
- 电子书：可借 7 天，有文件大小
- 工具书：可借 3 天，只能在馆内短期借阅

它们都有 `isbn`、`title`、`author`，都需要描述自己、都需要告诉别人「能借多久」。

如果写三个互不相关的类：

```python
class PaperBook:
    ...

class EBook:
    ...

class ReferenceBook:
    ...
```

那么「打印所有书的借阅规则」时，你只能这样：

```python
for book in books:
    if isinstance(book, PaperBook):
        print(f"可借 {book.paper_days} 天")
    elif isinstance(book, EBook):
        print(f"可借 {book.ebook_days} 天")
    elif isinstance(book, ReferenceBook):
        print(f"可借 {book.ref_days} 天")
```

每加一种书，就要改这个循环。这不是多态，这是「用 `if` 模拟多态」。

我们希望写成：

```python
for book in books:
    print(f"可借 {book.loan_days} 天")
```

不管具体是什么书，只要它有 `loan_days`，循环就不用改。

---

## 3.2 先运行

```bash
python -m examples.ch03_books
```

输出：

```text
《Python 编程》 / 张三（纸质书，520 页），可借 14 天
《流畅的 Python》 / 李四（电子书，8.5 MB），可借 7 天
《辞海》 / 王五（工具书，仅供馆内查阅），可借 3 天
Book 是抽象类，不能直接实例化
paper 是 Book 的实例吗？ True
```

完整代码在 [`examples/ch03_books.py`](../examples/ch03_books.py)：

```python
from __future__ import annotations

from abc import ABC, abstractmethod


class Book(ABC):
    def __init__(self, isbn: str, title: str, author: str) -> None:
        self.isbn = isbn
        self.title = title
        self.author = author

    @property
    @abstractmethod
    def loan_days(self) -> int:
        ...

    def describe(self) -> str:
        return f"《{self.title}》 / {self.author}"

    def loan_policy(self) -> str:
        return f"{self.describe()}，可借 {self.loan_days} 天"


class PaperBook(Book):
    def __init__(
        self,
        isbn: str,
        title: str,
        author: str,
        pages: int,
    ) -> None:
        super().__init__(isbn, title, author)
        self.pages = pages

    @property
    def loan_days(self) -> int:
        return 14

    def describe(self) -> str:
        return f"{super().describe()}（纸质书，{self.pages} 页）"


class EBook(Book):
    def __init__(
        self,
        isbn: str,
        title: str,
        author: str,
        file_size_mb: float,
    ) -> None:
        super().__init__(isbn, title, author)
        self.file_size_mb = file_size_mb

    @property
    def loan_days(self) -> int:
        return 7

    def describe(self) -> str:
        return f"{super().describe()}（电子书，{self.file_size_mb} MB）"


class ReferenceBook(Book):
    @property
    def loan_days(self) -> int:
        return 3

    def describe(self) -> str:
        return f"{super().describe()}（工具书，仅供馆内查阅）"


def main() -> None:
    books: list[Book] = [
        PaperBook("978-7-111-40701-0", "Python 编程", "张三", 520),
        EBook("978-7-115-54608-7", "流畅的 Python", "李四", 8.5),
        ReferenceBook("978-7-5326-0000-0", "辞海", "王五"),
    ]

    for book in books:
        print(book.loan_policy())

    try:
        Book("000", "抽象书", "无名")
    except TypeError:
        print("Book 是抽象类，不能直接实例化")

    print("paper 是 Book 的实例吗？", isinstance(books[0], Book))


if __name__ == "__main__":
    main()
```

---

## 3.3 继承的基本语法

```python
class PaperBook(Book):
    ...
```

读作：`PaperBook` 继承自 `Book`。

- `Book` 是父类（基类、超类）
- `PaperBook` 是子类（派生类）
- `PaperBook` 自动 type="拥有" `Book` 的属性和方法

```python
paper = PaperBook("...", "Python 编程", "张三", 520)
print(paper.title)   # Python 编程，来自 Book.__init__
```

继承表达的是 **is-a（是一个）** 关系：

> 纸质书 **是一种** 书。
>
> 所以 `PaperBook` 继承 `Book` 是合理的。

反过来就不合理：

> 图书馆 **是一个** 书？不是。所以 `Library` 不应该继承 `Book`。

这是判断继承是否合适的第一个问题：**子类能不能用「是一个」造句？**

---

## 3.4 `super()`：先让父类把该做的做了

```python
class PaperBook(Book):
    def __init__(self, isbn, title, author, pages):
        super().__init__(isbn, title, author)
        self.pages = pages
```

`super().__init__(...)` 调用父类的初始化方法，把 `isbn`、`title`、`author` 交给 `Book` 处理。

为什么不能直接写：

```python
self.isbn = isbn
self.title = title
self.author = author
```

可以，但不好。因为父类以后如果增加了初始化逻辑（比如校验 ISBN），你这边就漏掉了。**让每一层只负责自己的部分**，是继承能维护的前提。

### `super()` 不是「父类对象」

```python
super().describe()
```

它的意思是：按照方法解析顺序（MRO），找到当前类的**下一个**类，调用它的 `describe`。在单继承里，通常就是父类。

多继承时 `super()` 的规则更复杂，本课程不展开。你只需要记住：

> 子类重写 `__init__` 时，通常先调用 `super().__init__(...)`。

---

## 3.5 重写（override）

子类可以重新定义父类的方法：

```python
class PaperBook(Book):
    def describe(self) -> str:
        return f"{super().describe()}（纸质书，{self.pages} 页）"
```

这叫重写。调用 `paper.describe()` 时，Python 优先找 `PaperBook` 自己的 `describe`，找到就不再去父类找。

在重写里调用 `super().describe()` 可以复用父类逻辑，再追加子类特有的信息。这是很常见的写法。

---

## 3.6 多态：同一个调用，不同行为

```python
books: list[Book] = [
    PaperBook(...),
    EBook(...),
    ReferenceBook(...),
]

for book in books:
    print(book.loan_policy())
```

循环里只写了 `book.loan_policy()`，没有判断具体类型。但每个对象执行的结果不同：

```text
纸质书：14 天
电子书：7 天
工具书：3 天
```

这就是多态：

> **调用方只依赖统一的接口，具体执行哪种行为由对象的实际类型决定。**

多态的好处是「对扩展开放，对修改关闭」：

- 新增 `AudioBook`，只要实现 `loan_days` 和 `describe`，循环不用改
- 调用方不需要知道所有子类
- 新增类型不会引发一连串 `if/elif`

---

## 3.7 抽象基类：强制子类实现接口

```python
from abc import ABC, abstractmethod


class Book(ABC):
    @property
    @abstractmethod
    def loan_days(self) -> int:
        ...
```

`ABC` 是抽象基类。`@abstractmethod` 标记的方法**必须由子类实现**，否则子类也不能实例化。

试试：

```python
Book("000", "抽象书", "无名")
```

会抛 `TypeError`，因为 `Book` 还有抽象方法没实现。

这带来两个好处：

1. **文档化**：一看基类就知道子类必须提供什么
2. **尽早报错**：少实现一个方法，在创建对象时就暴露，而不是等到调用时才 `AttributeError`

### 抽象方法可以有实现吗？

可以：

```python
@abstractmethod
def loan_days(self) -> int:
    return 7
```

子类仍然必须重写，但可以通过 `super().loan_days()` 复用默认值。初学阶段不用这么写，知道有这回事即可。

### 抽象基类 vs 普通父类

| 方式 | 适用场景 |
| :--- | :--- |
| 普通父类 | 有可复用的具体实现，子类只是扩展 |
| 抽象基类 | 只定义「必须有什么」，具体实现交给子类 |

本章的 `Book` 有共同的 `__init__` 和 `describe`，所以它是「有实现的抽象基类」，两种特点都有。

---

## 3.8 里氏替换原则（LSP）

名字很吓人，意思很简单：

> **子类对象应该能在任何使用父类的地方替换父类，而且不破坏程序的行为。**

例如，所有接受 `Book` 的函数，都应该能接受 `PaperBook`、`EBook`、`ReferenceBook`：

```python
def print_policy(book: Book) -> None:
    print(book.loan_policy())

for book in books:
    print_policy(book)
```

如果 `ReferenceBook` 的 `loan_policy()` 突然返回 `None`，或者抛出一个调用方完全没准备的异常，就破坏了 LSP。

### 一个反例

```python
class EBook(Book):
    @property
    def loan_days(self) -> int:
        raise NotImplementedError("电子书不支持借阅")
```

如果调用方拿到的是 `Book`，它默认「所有书都能借」。结果电子书一借就炸。这不是多态，这是给调用方埋雷。

正确的做法是重新设计抽象：

- 如果有些书不能借，就不要让「可借」成为所有书的统一承诺
- 可以拆成 `Borrowable` 和 `Readable` 两个接口
- 或者让 `Library` 在借阅前检查能力

**不要用继承强行套一个不成立的「是一个」。**

---

## 3.9 继承 vs 组合：先别急着继承

继承最大的诱惑是「复用代码」。但继承是一种**强耦合**：

- 子类依赖父类的实现细节
- 父类一改，所有子类都可能受影响
- 层级一深，理解成本急剧上升

很多「继承」场景其实应该是「组合」：

```python
class Shelf:
    def __init__(self) -> None:
        self._books: list[Book] = []

    def add(self, book: Book) -> None:
        self._books.append(book)

    def find(self, isbn: str) -> Book | None:
        for book in self._books:
            if book.isbn == isbn:
                return book
        return None
```

`Shelf` **有一个** `Book` 列表，而不是 **是一个** `Book`。这就是组合。

判断口诀：

| 关系 | 用 |
| :--- | :--- |
| 子类 **是一个** 父类 | 继承 |
| 对象 **有一个** 另一个对象 | 组合 |
| 只是想复用几个函数 | 组合 / 函数，不要继承 |

第 04 章会大量使用组合来搭 `Library`。

---

## 3.10 多继承与 MRO（了解即可）

Python 支持多继承：

```python
class A:
    def hello(self) -> str:
        return "A"

class B:
    def hello(self) -> str:
        return "B"

class C(A, B):
    pass

print(C().hello())   # A
```

`C` 会按照方法解析顺序（MRO）查找方法：

```python
print(C.__mro__)
# (<class 'C'>, <class 'A'>, <class 'B'>, <class 'object'>)
```

**初学阶段不要用多继承。** 它容易造成「菱形继承」和方法来源不清晰。绝大多数业务代码用单继承 + 组合就够了。

---

## 3.11 动手改

在 `examples/ch03_books.py` 中：

1. 新增 `AudioBook`，可借 10 天，有 `duration_hours` 属性，`describe` 输出「有声书，12.5 小时」。
2. 把它加入 `books` 列表，确认循环不需要改。
3. 试着删掉 `AudioBook.loan_days`，运行看看会发生什么。

参考实现：

```python
class AudioBook(Book):
    def __init__(
        self,
        isbn: str,
        title: str,
        author: str,
        duration_hours: float,
    ) -> None:
        super().__init__(isbn, title, author)
        self.duration_hours = duration_hours

    @property
    def loan_days(self) -> int:
        return 10

    def describe(self) -> str:
        return f"{super().describe()}（有声书，{self.duration_hours} 小时）"
```

删掉 `loan_days` 后，`AudioBook` 仍然是抽象类，实例化时会报 `TypeError`。这正是抽象基类在帮你提前发现问题。

---

## 3.12 常见坑

### 坑 1：忘记调用 `super().__init__`

```python
class EBook(Book):
    def __init__(self, isbn, title, author, size):
        self.file_size_mb = size
```

结果 `ebook.title` 不存在。子类只初始化了自己的字段。

### 坑 2：为了复用代码而继承

```python
class Library(Book):   # 图书馆不是书
    ...
```

这种继承会让 `Library` 莫名其妙拥有 `loan_days`、`describe`。关系不成立，后面会越来越别扭。

### 坑 3：继承层级过深

```text
Book -> PaperBook -> ChinesePaperBook -> ChinesePaperBookWithDustJacket
```

每加一层，理解和修改成本都上升。通常 2-3 层就该考虑组合或拆分。

### 坑 4：子类改变父类的行为约定

父类说「返回天数」，子类返回 `None`；父类说「不会抛异常」，子类抛得满天飞。调用方按父类约定写代码，就会崩。

### 坑 5：用 `isinstance` 写一长串分支

```python
if isinstance(book, PaperBook):
    ...
elif isinstance(book, EBook):
    ...
```

如果每个分支都是在问「你是什么类型」，通常说明应该把行为放到子类里，用多态解决。

---

## 3.13 本章练习

### 练习 A：`Magazine`

新增 `Magazine`（杂志）：

- 可借 5 天
- 有 `issue`（期号）属性
- `describe` 输出「杂志，2026 年第 10 期」

### 练习 B：拆分接口

假设有些书可以借，有些只能阅览：

- `Borrowable`：`loan_days`
- `Readable`：`read_url` 或 `shelf_location`

重新设计 `Book` 家族，让 `ReferenceBook` 只实现 `Readable`，纸质书和电子书实现 `Borrowable`。

思考：`Library.borrow()` 应该如何判断一本书能不能借？用 `isinstance`，还是用 `Protocol`？第 07 章会讲后者。

### 练习 C：找错误

下面代码有什么问题？

```python
class Book:
    def __init__(self, title: str) -> None:
        self.title = title

class EBook(Book):
    def __init__(self, title: str, size: float) -> None:
        self.size = size

ebook = EBook("Python", 8.0)
print(ebook.title)
```

---

## 3.14 检查点

1. 继承表达的是什么关系？举一个合理的例子和一个不合理的例子。
2. `super().__init__(...)` 做了什么？不调用会怎样？
3. 多态解决了什么问题？为什么它比一长串 `isinstance` 更好？
4. `ABC` 和 `@abstractmethod` 的作用是什么？
5. 里氏替换原则用一句话怎么说？
6. 什么时候应该用组合而不是继承？

如果第 2、3、6 题能说清，就可以进入组合的世界了。

---

[← 上一章：封装](./02_encapsulation.md) | [下一章：组合 →](./04_composition.md)